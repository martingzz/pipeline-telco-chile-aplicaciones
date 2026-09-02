from __future__ import print_function

import argparse

import torch
import torch.optim as optim
import torch.utils.data.distributed

import pandas as pd
import numpy as np

import random

import os

import time

from importlib.machinery import SourceFileLoader

# Training settings
parser = argparse.ArgumentParser(description='DeepGravity')
parser.add_argument('--batch_size', type=int, default=1, metavar='N',
                    help='input batch size for training (default: 1)')
parser.add_argument('--test-batch-size', type=int, default=1, metavar='N',
                    help='input batch size for testing (default: 1)')
parser.add_argument('--epochs', type=int, default=15, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=5e-6, metavar='LR',
                    help='learning rate (default: 5e-6)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                    help='SGD momentum (default: 0.9)')
parser.add_argument('--seed', type=int, default=1234, metavar='S',
                    help='random seed (default: 1234)')
parser.add_argument('--log-interval', type=int, default=1, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--device', default='cpu',
                    help='Wheter this is running on cpu or gpu')
parser.add_argument('--mode', default='train', help='Can be train or test')
# Model arguments
parser.add_argument('--tessellation-area', default='United Kingdom',
                    help='The area to tessel if a tessellation is not provided')
parser.add_argument('--tessellation-size', type=int, default=25000,
                    help='The tessellation size (meters) if a tessellation is not provided')
parser.add_argument('--dataset', default='new_york', help='The dataset to use')

# Dataset arguments 
parser.add_argument('--tile-id-column', default='tile_ID', help='Column name of tile\'s identifier')
parser.add_argument('--tile-geometry', default='geometry', help='Column name of tile\'s geometry')

parser.add_argument('--oa-id-column', default='oa_ID', help='Column name of oa\'s identifier')
parser.add_argument('--oa-geometry', default='geometry', help='Column name of oa\'s geometry')

parser.add_argument('--flow-origin-column', default='origin', help='Column name of flows\' origin')
parser.add_argument('--flow-destination-column', default='destination', help='Column name of flows\' destination')
parser.add_argument('--flow-flows-column', default='flow', help='Column name of flows\' actual value')

args = parser.parse_args()

# global settings
model_type = 'DG'
data_name = args.dataset

# random seeds
torch.manual_seed(args.seed)
np.random.seed(args.seed)
random.seed(args.seed)

# loading DataLoader and utilities
path = './data_loader.py'
dgd = SourceFileLoader('dg_data', path).load_module()
path = './utils.py'
utils = SourceFileLoader('utils', path).load_module()

# set the device 
args.cuda = args.device.find("gpu") != -1

if args.device.find("gpu") != -1:
    torch.cuda.manual_seed(args.seed)
    torch_device = torch.device("cuda")
else:
    torch_device = torch.device("cpu")

# check if raw data exists and otherwise stop the execution
if not os.path.isdir('./data/' + data_name):
    raise ValueError('There is no dataset named ' + data_name + ' in ./data/')

db_dir = './data/' + data_name


def train(epoch):
    model.train()
    running_loss = 0.0
    training_acc = 0.0

    for batch_idx, data_temp in enumerate(train_loader):
        b_data = data_temp[0]
        b_target = data_temp[1]
        ids = data_temp[2]
        optimizer.zero_grad()
        loss = 0.0
        for data, target in zip(b_data, b_target):

            if args.cuda:
                data, target = data.cuda(), target.cuda()

            output = model.forward(data)
            loss += model.loss(output, target)

        loss.backward()
        optimizer.step()
        running_loss += loss.item()

        if batch_idx % args.log_interval == 0:
            if batch_idx * len(b_data) == len(train_loader) - 1:
                print('Train Epoch: {} [{}/{} \tLoss: {:.6f}'.format(epoch, batch_idx * len(b_data), len(train_loader),
                                                                     loss.item() / args.batch_size))

    running_loss = running_loss / len(train_dataset)
    training_acc = training_acc / len(train_dataset)


def test():
    model.eval()
    with torch.no_grad():
        test_loss = 0.
        test_accuracy = 0.
        n_origins = 0
        for batch_idx, data_temp in enumerate(test_loader):
            b_data = data_temp[0]
            b_target = data_temp[1]
            ids = data_temp[2]
            test_loss = 0.0

            for data, target in zip(b_data, b_target):
                if args.cuda:
                    data, target = data.cuda(), target.cuda()

                output = model.forward(data)
                test_loss += model.loss(output, target).item()

                cpc = model.get_cpc(data, target)
                test_accuracy += cpc
                n_origins += 1

            break

        test_loss /= n_origins
        test_accuracy /= n_origins

def evaluate():
    """
    Evalúa como siempre (CPC por tile) y, además, vuelca:
      - la tabla completa locID vs cpc_num para TODAS las comunas del/los tiles TEST
      - el detalle OD observado y predicho (origin, destination, prob, y_obs, y_pred)
        SOLO DENTRO DEL MISMO TILE DE TEST DEL ORIGEN (edges_TEST_pairs.csv)
      - CPC_intra (clásico, escalando por O_i^intra observado) por tile
        y CPC_repo (del código original) por tile.

    Ajuste definitivo: auto-máscara de autoflujos (d=i) POR ORIGEN en evaluación:
      * Si para el origen i existe y_{i,i} > 0 en o2d2flow -> incluir d=i en su softmax intra-tile.
      * Si para el origen i NO existe y_{i,i} -> excluir d=i y renormalizar el softmax sobre el resto.
    """
    # --- Recorremos test_loader solo para identificar orígenes de TEST ---
    test_origins = []
    model.eval()
    with torch.no_grad():
        for data_temp in test_loader:
            ids = data_temp[2]
            for oa_id in ids:
                # oa_id es lista/tupla; el valor está en oa_id[0]
                test_origins.append(oa_id[0])

    unique_test_origins = sorted(set(test_origins))

    # --- Mapa OA -> tile (keys como strings) ---
    oa2tile = {oa: t for t, v in tileid2oa2features2vals.items() for oa in v.keys()}

    # --- Acumuladores: numerador de CPC por origen y detalle de aristas intra-tile ---
    loc2cpc_numerator = {}
    edges_rows = []

    # --- Cálculo por origen, con decisión de diagonal por-origen ---
    with torch.no_grad():
        for ori in unique_test_origins:
            tile_id = oa2tile[ori]
            # Destinos candidatos del MISMO tile
            dests_tile_all = sorted(tileid2oa2features2vals[str(tile_id)].keys())
            if not dests_tile_all:
                continue

            # Observados del origen (diccionario destino->flujo)
            d2f = o2d2flow.get(ori, {})

            # Incluir o no la diagonal PARA ESTE ORIGEN
            include_self = float(d2f.get(ori, 0.0)) > 0.0
            dests_tile = dests_tile_all if include_self else [d for d in dests_tile_all if d != ori]

            # Si quedó vacío (p.ej., tile unitario sin diagonal), saltamos
            if not dests_tile:
                continue

            # Features (ori, d) para todos los destinos evaluados
            feats_ij = [test_dataset.get_features(ori, d) for d in dests_tile]
            X = np.stack(feats_ij).astype(np.float32)  # [N_dest_tile_eval, dim_input]
            X_t = torch.from_numpy(X).to(torch_device)

            # Logits -> softmax sobre el subconjunto (posiblemente sin diagonal)
            logits = model.forward(X_t).squeeze()               # [N_dest_tile_eval]
            probs = torch.softmax(logits, dim=0).cpu().numpy()  # renormalizado

            # Observado intra-tile solo en los destinos evaluados
            y_obs = np.array([float(d2f.get(d, 0.0)) for d in dests_tile], dtype=np.float32)
            Oi_intra = float(y_obs.sum())  # O_i^{intra} coherente con el subconjunto elegido

            # Predicción de flujos intra-tile: ŷ_ij = O_i^{intra} · p_ij
            y_pred = probs * Oi_intra

            # Numerador del CPC por ORIGEN (coherente con el subconjunto elegido)
            cpc_num_i = float(2.0 * np.minimum(y_pred, y_obs).sum())
            loc2cpc_numerator[ori] = cpc_num_i

            # Guardar detalle de edges
            for d, p, y_o, y_p in zip(dests_tile, probs, y_obs, y_pred):
                edges_rows.append({
                    "origin": str(ori),
                    "destination": str(d),
                    "prob": float(p),
                    "y_obs": float(y_o),
                    "y_pred": float(y_p)
                })

    # === CPC_repo por tile (igual lógica que antes) e impresión de todas las comunas TEST ===
    edf = pd.DataFrame.from_dict(
        loc2cpc_numerator, columns=['cpc_num'], orient='index'
    ).reset_index().rename(columns={'index': 'locID'})

    print("locID vs cpc_num (todas las comunas del/los tiles de TEST):")
    if not edf.empty:
        print(edf.to_string(index=False))  # imprime TODAS, sin truncar
    else:
        print("(sin orígenes de test válidos)")

    edf['tile'] = edf['locID'].apply(lambda x: oa2tile[x])
    # Outflow GLOBAL observado por origen (para el denominador estilo repo)
    edf['tot_flow'] = edf['locID'].apply(
        lambda x: sum(o2d2flow.get(x, {}).values()) if x in o2d2flow else 1e-6
    )

    cpc_repo_df = pd.DataFrame(
        edf.groupby('tile').apply(
            lambda x: x['cpc_num'].sum() / (2.0 * x['tot_flow'].sum() if x['tot_flow'].sum() > 0 else 1e-9)
        ),
        columns=['cpc_repo']
    ).reset_index()

    # === Guardar detalle OD (observado/predicho, INTRA-TILE) ===
    edges_df = pd.DataFrame(edges_rows)
    os.makedirs("./results", exist_ok=True)
    edges_path = "./results/edges_TEST_pairs.csv"
    edges_df.to_csv(edges_path, index=False)
    print(f"Guardado detalle OD (observado/predicho, INTRA-TILE) en {edges_path}")

    # === CPC_intra por tile, usando SOLO edges intra-tile (con diagonal por-origen ya aplicada) ===
    if not edges_df.empty:
        edges_df['tile'] = edges_df['origin'].map(oa2tile)

        def cpc_intra_from_edges(df_tile):
            y_pred_sum = df_tile['y_pred'].sum()
            y_obs_sum  = df_tile['y_obs'].sum()
            num = 2.0 * np.minimum(df_tile['y_pred'], df_tile['y_obs']).sum()
            den = y_pred_sum + y_obs_sum if (y_pred_sum + y_obs_sum) > 0 else 1e-9
            cpc_intra = float(num / den)

            # "Ceiling" estilo repo: fracción del outflow global que permanece intra-tile (observado)
            origins = df_tile['origin'].unique().tolist()
            O_global_sum = float(sum(sum(o2d2flow.get(o, {}).values()) for o in origins))
            ceiling = float(y_obs_sum / O_global_sum) if O_global_sum > 0 else 0.0

            return pd.Series({
                'cpc_intra': cpc_intra,
                'ceiling_repo_style': ceiling,
                'y_pred_intra_sum': y_pred_sum,
                'y_obs_intra_sum': y_obs_sum
            })

        cpc_intra_df = edges_df.groupby('tile', as_index=False).apply(cpc_intra_from_edges)
    else:
        cpc_intra_df = pd.DataFrame(columns=['tile','cpc_intra','ceiling_repo_style','y_pred_intra_sum','y_obs_intra_sum'])

    # === Merge de métricas y guardado unificado ===
    cpc_df = pd.merge(cpc_repo_df, cpc_intra_df, on='tile', how='outer')
    fname = './results/tile2cpc_{}_{}.csv'.format(model_type, args.dataset)
    cpc_df.to_csv(fname, index=False)

    # Prints resumen
    if not cpc_df.empty:
        print(
            "Average CPC_intra of test tiles: "
            f"{cpc_df['cpc_intra'].mean():.4f}  stdev: {cpc_df['cpc_intra'].std():.4f}"
        )
        print(
            "Average CPC_repo of test tiles:  "
            f"{cpc_df['cpc_repo'].mean():.4f}  stdev: {cpc_df['cpc_repo'].std():.4f}"
        )
        print(
            "Average ceiling (y_obs_intra / sum_Oi_global): "
            f"{cpc_df['ceiling_repo_style'].mean():.4f}"
        )
    else:
        print("Sin métricas: no hubo edges/orígenes válidos en TEST.")

utils.tessellation_definition(db_dir, args.tessellation_area, args.tessellation_size)

tileid2oa2features2vals, oa_gdf, flow_df, oa2pop, oa2features, od2flow, oa2centroid = utils.load_data(db_dir,
                                                                                                      args.tile_id_column,
                                                                                                      args.tile_geometry,
                                                                                                      args.oa_id_column,
                                                                                                      args.oa_geometry,
                                                                                                      args.flow_origin_column,
                                                                                                      args.flow_destination_column,
                                                                                                      args.flow_flows_column)

oa2features = {oa: [np.log(oa2pop[oa])] + feats for oa, feats in oa2features.items()}

o2d2flow = {}
for (o, d), f in od2flow.items():
    try:
        d2f = o2d2flow[o]
        d2f[d] = f
    except KeyError:
        o2d2flow[o] = {d: f}

train_dataset_args = {'tileid2oa2features2vals': tileid2oa2features2vals,
                      'o2d2flow': o2d2flow,
                      'oa2features': oa2features,
                      'oa2pop': oa2pop,
                      'oa2centroid': oa2centroid,
                      'dim_dests': 512,
                      'frac_true_dest': 0.0,
                      'model': model_type}

test_dataset_args = {'tileid2oa2features2vals': tileid2oa2features2vals,
                     'o2d2flow': o2d2flow,
                     'oa2features': oa2features,
                     'oa2pop': oa2pop,
                     'oa2centroid': oa2centroid,
                     'dim_dests': int(1e9),
                     'frac_true_dest': 0.0,
                     'model': model_type}

# datasets
train_data = [oa for t in pd.read_csv(db_dir + '/processed/train_tiles.csv', header=None, dtype=object)[0].values for oa
              in tileid2oa2features2vals[str(t)].keys()]
test_data = [oa for t in pd.read_csv(db_dir + '/processed/test_tiles.csv', header=None)[0].values for oa in
             tileid2oa2features2vals[str(t)].keys()]

train_dataset = dgd.FlowDataset(train_data, **train_dataset_args)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size)

test_dataset = dgd.FlowDataset(test_data, **test_dataset_args)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=args.test_batch_size)

dim_input = len(train_dataset.get_features(train_data[0], train_data[0]))

if args.mode == 'train':

    model = utils.instantiate_model(oa2centroid, oa2features, oa2pop, dim_input, device=torch_device)
    if args.device.find("gpu") != -1:
        model.cuda()

    optimizer = optim.RMSprop(model.parameters(), lr=args.lr, momentum=args.momentum)

    t0 = time.time()
    test()
    for epoch in range(1, args.epochs + 1):
        # set new random seeds
        torch.manual_seed(args.seed + epoch)
        np.random.seed(args.seed + epoch)
        random.seed(args.seed + epoch)

        train(epoch)
        test()

    t1 = time.time()
    print("Total training time: %s seconds" % (t1 - t0))

    fname = './results/model_{}_{}.pt'.format(model_type, args.dataset)
    print('Saving model to {} ...'.format(fname))
    torch.save({'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict()
                }, fname)

    print('Computing the CPC on test set, loc2cpc_numerator ...')

    evaluate()


else:

    model = utils.instantiate_model(oa2centroid, oa2features, oa2pop, dim_input, device=torch_device)
    optimizer = optim.RMSprop(model.parameters(), lr=args.lr, momentum=args.momentum)

    checkpoint = torch.load('./results/model_' + model_type + '_' + args.dataset + '.pt')
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

    evaluate()
