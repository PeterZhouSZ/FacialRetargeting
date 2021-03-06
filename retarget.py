import os
import numpy as np
from tqdm import tqdm
from scipy.linalg import solve

import multiprocessing as mp
from functools import partial

from utils.load_data import load_training_seq
from utils.normalize_positions import normalize_positions
from utils.align_to_head_markers import align_to_head_markers
from utils.modify_axis import modify_axis
from utils.compute_delta import compute_delta
from src.ERetarget import ERetarget


def get_w(i, eRetarget, delta_af):
    eRetarget.set_af(delta_af[i])
    A, b = eRetarget.get_dERetarget()
    return solve(A, b)


if __name__ == '__main__':
    pool = mp.Pool(processes=4)
    #### missing: get blendshapes and marker data from maya here

    # define parameters
    ref_actor_pose = 'data/David_neutral_pose.npy'
    load_folder = "data/"
    delta_p_name = "David_based_Louise_personalized_blendshapes_v3_norm_EMatch.npy"
    LdV_name = "LdV_louise.npy"
    load_sequence_folder = "D:/MoCap_Data/David/NewSession_labeled/"
    # sequence_name = "AngerTrail05.c3d"
    sequence_name = "HappyTrail01.c3d"
    # sequence_name = "FearTrail03.c3d"
    # sequence_name = "NeutralTrail14.c3d"
    num_markers = 45
    save_folder = "data/"
    save_name = "weights_David2Louise_retarget_Happy_500_v3"
    # save_name = "weights_David2Louise_retarget_FearTrail"

    # ----------------------- data -------------------------
    # load data
    delta_p = np.load(os.path.join(load_folder, delta_p_name))
    print("max delta_p", np.amax(delta_p))
    LdV = np.load(os.path.join(load_folder, LdV_name))
    # LdV /= np.linalg.norm(LdV)  # todo normalize dV and not LdV?
    print("max ldv", np.amax(LdV))

    # load reference actor pose
    ref_actor_pose = np.load(ref_actor_pose)
    # align sequence with the head markers
    head_markers = range(np.shape(ref_actor_pose)[0] - 4, np.shape(ref_actor_pose)[0] - 1)  # use only 3 markers
    ref_actor_pose = align_to_head_markers(ref_actor_pose, ref_idx=head_markers)
    ref_actor_pose = ref_actor_pose[:-4, :]  # remove HEAD markers
    # modify axis from xzy to xyz to match the scatter blendshape axis orders
    ref_actor_pose = modify_axis(ref_actor_pose, order='xzy2xyz', inverse_z=True)
    # normalize reference (neutral) actor positions
    ref_actor_pose, min_af, max_af = normalize_positions(ref_actor_pose, return_min=True, return_max=True)

    # load sequence to retarget
    af = load_training_seq(load_sequence_folder, sequence_name, num_markers)
    af = align_to_head_markers(af, ref_idx=head_markers)
    af = af[:, :-4, :]  # remove HEAD markers
    # modify axis from xyz to xzy to match the scatter blendshape axis orders
    af = modify_axis(af, order='xzy2xyz', inverse_z=True)
    af = normalize_positions(af, min_pos=min_af, max_pos=max_af)

    # compute delta af
    delta_af = compute_delta(af, ref_actor_pose, norm_thresh=2)

    print("[data] Finish loading data")
    print("[data] shape delta_p", np.shape(delta_p))
    print("[data] shape LdV", np.shape(LdV))
    print("[data] shape delta_af", np.shape(delta_af))
    num_frames = np.shape(delta_af)[0]
    num_blendshapes = np.shape(delta_p)[0]
    num_markers = np.shape(delta_p)[1] / 3
    print("[data] num frames:", num_frames)
    print("[data] num blendshapes:", num_blendshapes)
    print("[data] num_markers:", num_markers)
    print()

    # ----------------------- ERetarget -------------------------
    eRetarget = ERetarget(delta_p, LdV)

    # weights = []
    # for i in tqdm(range(500)):
    # # for i in tqdm(range(1589, 1590)):
    # # for i in tqdm(range(num_frames)):
    #     eRetarget.set_af(delta_af[i])
    #     A, b = eRetarget.get_dERetarget(L2=use_L2)
    #     w = solve(A, b)
    #     weights.append(w)

    # multiprocessing
    p_get_w = partial(get_w, eRetarget=eRetarget, delta_af=delta_af)
    weights = pool.map(p_get_w, tqdm(range(15000)))
    pool.close()

    print("[Retarget] shape weights", np.shape(weights))

    # normalize weights
    weights = np.array(weights)
    print("shape weights", np.shape(weights))
    print(weights[:, 0])
    max_weights = np.amax(weights)
    min_weights = np.amin(weights)
    max_index = np.argmax(weights)
    min_index = np.argmin(weights)
    print("max weights", max_weights, "at", max_index)
    print("min weights", min_weights, "at", min_index)
    # weights /= np.amax(weights)
    # save
    np.save(os.path.join(save_folder, save_name), weights)
    print("weights save as:", os.path.join(save_folder, save_name))
    print("max weights", np.amax(weights), "at", max_index)
    print("min weights", np.amin(weights), "at", min_index)


