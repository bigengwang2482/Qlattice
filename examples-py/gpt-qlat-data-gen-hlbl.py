#!/usr/bin/env python3

from auto_contractor.operators import *

import functools
import math
import os
import time
import importlib
import sys
from copy import deepcopy

import qlat_gpt as qg

from qlat_scripts.v1 import *

is_cython = False

# ----

load_path_list[:] = [
        "results",
        "/lustre/orion/lgt119/proj-shared/ljin/qcddata4",
        "/lustre/orion/lgt119/proj-shared/ljin/qcddata5",
        ]

# ----

@q.timer
def get_cexpr_meson_corr():
    fn_base = "cache/auto_contract_cexpr/get_cexpr_meson_corr"
    def calc_cexpr():
        diagram_type_dict = dict()
        diagram_type_dict[((('x_1', 'x_2'), 1), (('x_2', 'x_1'), 1))] = 'Type1'
        diagram_type_dict[((('x_1', 'x_1'), 1), (('x_2', 'x_2'), 1))] = None
        exprs = [
                mk_fac(1) + f"1",
                mk_pi_p("x_2", True)    * mk_pi_p("x_1")             + f"pi+^dag(0) * pi+(-tsep)",
                mk_k_p("x_2", True)     * mk_k_p("x_1")              + f"K+^dag(0) * K+(-tsep)",
                mk_sw5("x_2")           * mk_pi_p("x_1")             + f"sw5(0) * pi+(-tsep)",
                mk_sw5("x_2")           * mk_k_p("x_1")              + f"sw5(0) * K+(-tsep)",
                mk_sw5("x_2")           * mk_j5pi_mu("x_1", 3, True) + f"sw5(0) * j5pi_t^dag(-tsep)",
                mk_sw5("x_2")           * mk_j5k_mu("x_1", 3, True)  + f"sw5(0) * j5k_t^dag(-tsep)",
                mk_jw_a_mu("x_2", 3)    * mk_pi_p("x_1")             + f"jw_a_t(0) * pi+(-tsep)",
                mk_jw_a_mu("x_2", 3)    * mk_k_p("x_1")              + f"jw_a_t(0) * K+(-tsep)",
                mk_jw_a_mu("x_2", 3)    * mk_j5pi_mu("x_1", 3, True) + f"jw_a_t(0) * j5pi_t^dag(-tsep)",
                mk_jw_a_mu("x_2", 3)    * mk_j5k_mu("x_1", 3, True)  + f"jw_a_t(0) * j5k_t^dag(-tsep)",
                mk_a0_p("x_2", True)    * mk_a0_p("x_1")             + f"a0+^dag(0) * a0+(-tsep)",
                mk_kappa_p("x_2", True) * mk_kappa_p("x_1")          + f"kappa+^dag(0) * kappa+(-tsep)",
                mk_j_mu("x_2", 3)       * mk_j_mu("x_1", 3)          + f"j_t(0) * j_t(-tsep)",
                sum([ mk_j_mu("x_2", mu) * mk_j_mu("x_1", mu) for mu in range(4) ])
                + f"j_mu(0) * j_mu(-tsep)",
                sum([ mk_jw_a_mu("x_2", mu) * mk_j5pi_mu("x_1", mu, True) for mu in range(4) ])
                + f"jw_a_mu(0) * j5pi_mu^dag(-tsep)",
                sum([ mk_jw_a_mu("x_2", mu) * mk_j5k_mu("x_1", mu, True) for mu in range(4) ])
                + f"jw_a_mu(0) * j5k_mu^dag(-tsep)",
                ]
        cexpr = contract_simplify_compile(*exprs, is_isospin_symmetric_limit=True, diagram_type_dict=diagram_type_dict)
        return cexpr
    return cache_compiled_cexpr(calc_cexpr, fn_base, is_cython=is_cython)

@q.timer_verbose
def auto_contract_meson_corr(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob):
    fname = q.get_fname()
    fn = f"{job_tag}/auto-contract/traj-{traj}/meson_corr.lat"
    if get_load_path(fn) is not None:
        return
    cexpr = get_cexpr_meson_corr()
    expr_names = get_expr_names(cexpr)
    total_site = q.Coordinate(get_param(job_tag, "total_site"))
    t_size = total_site[3]
    get_prop = get_get_prop()
    psel_prob = get_psel_prob()
    fsel_prob = get_fsel_prob()
    psel = psel_prob.psel
    fsel = fsel_prob.fsel
    if not fsel.is_containing(psel):
        q.displayln_info(-1, f"WARNING: fsel is not containing psel. The probability weighting may be wrong.")
    fsel_n_elems = fsel.n_elems()
    fsel_prob_arr = fsel_prob[:].ravel()
    psel_prob_arr = psel_prob[:].ravel()
    xg_fsel_arr = fsel.to_psel_local()[:]
    geo = q.Geometry(total_site, 1)
    total_volume = geo.total_volume()
    def load_data():
        t_t_list = get_mpi_chunk(
                [ (t_src, t_snk,) for t_snk in range(total_site[3]) for t_src in range(total_site[3]) ],
                rng_state = None)
        for t_src, t_snk in t_t_list:
            yield t_src, t_snk
    @q.timer
    def feval(args):
        t_src, t_snk = args
        t = (t_snk - t_src) % total_site[3]
        pd = {
                "x_2" : ("wall", t_snk,),
                "x_1" : ("wall", t_src,),
                "size" : total_site,
                }
        val = eval_cexpr(cexpr, positions_dict=pd, get_prop=get_prop)
        return val, t
    def sum_function(val_list):
        values = np.zeros((total_site[3], len(expr_names),), dtype=complex)
        for val, t in val_list:
            values[t] += val
        return q.glb_sum(values.transpose(1, 0))
    auto_contractor_chunk_size = get_param(job_tag, "measurement", "auto_contractor_chunk_size", default=128)
    q.timer_fork(0)
    res_sum = q.parallel_map_sum(feval, load_data(), sum_function=sum_function, chunksize=auto_contractor_chunk_size)
    q.displayln_info(f"{fname}: timer_display for parallel_map_sum")
    q.timer_display()
    q.timer_merge()
    res_sum *= 1.0 / total_site[3]
    assert q.qnorm(res_sum[0] - 1.0) < 1e-10
    ld = q.mk_lat_data([
        [ "expr_name", len(expr_names), expr_names, ],
        [ "t_sep", t_size, [ str(q.rel_mod(t, t_size)) for t in range(t_size) ], ],
        ])
    ld.from_numpy(res_sum)
    ld.save(get_save_path(fn))
    q.displayln_info(f"CHECK: {fname}: ld sig: {q.get_double_sig(ld, q.RngState()):.5E}")

@q.timer_verbose
def auto_contract_meson_corr_psnk(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob):
    fname = q.get_fname()
    fn = f"{job_tag}/auto-contract/traj-{traj}/meson_corr_psnk.lat"
    if get_load_path(fn) is not None:
        return
    cexpr = get_cexpr_meson_corr()
    expr_names = get_expr_names(cexpr)
    total_site = q.Coordinate(get_param(job_tag, "total_site"))
    t_size = total_site[3]
    get_prop = get_get_prop()
    psel_prob = get_psel_prob()
    fsel_prob = get_fsel_prob()
    psel = psel_prob.psel
    fsel = fsel_prob.fsel
    if not fsel.is_containing(psel):
        q.displayln_info(-1, f"WARNING: fsel is not containing psel. The probability weighting may be wrong.")
    fsel_n_elems = fsel.n_elems()
    fsel_prob_arr = fsel_prob[:].ravel()
    psel_prob_arr = psel_prob[:].ravel()
    xg_fsel_arr = fsel.to_psel_local()[:]
    geo = q.Geometry(total_site, 1)
    total_volume = geo.total_volume()
    def load_data():
        for t_src in range(total_site[3]):
            for idx in range(fsel_n_elems):
                yield t_src, idx
    @q.timer
    def feval(args):
        t_src, idx = args
        xg_snk = tuple(xg_fsel_arr[idx])
        prob_snk = fsel_prob_arr[idx]
        t = (xg_snk[3] - t_src) % total_site[3]
        pd = {
                "x_2" : ("point-snk", xg_snk,),
                "x_1" : ("wall", t_src,),
                "size" : total_site,
                }
        val = eval_cexpr(cexpr, positions_dict=pd, get_prop=get_prop)
        return val / prob_snk, t
    def sum_function(val_list):
        values = np.zeros((total_site[3], len(expr_names),), dtype=complex)
        for val, t in val_list:
            values[t] += val
        return values.transpose(1, 0)
    auto_contractor_chunk_size = get_param(job_tag, "measurement", "auto_contractor_chunk_size", default=128)
    q.timer_fork(0)
    res_sum = q.glb_sum(
            q.parallel_map_sum(feval, load_data(), sum_function=sum_function, chunksize=auto_contractor_chunk_size))
    q.displayln_info("timer_display for auto_contract_meson_corr_psnk")
    q.timer_display()
    q.timer_merge()
    res_sum *= 1.0 / total_volume
    q.displayln_info(0, res_sum[0])
    ld = q.mk_lat_data([
        [ "expr_name", len(expr_names), expr_names, ],
        [ "t_sep", t_size, [ str(q.rel_mod(t, t_size)) for t in range(t_size) ], ],
        ])
    ld.from_numpy(res_sum)
    ld.save(get_save_path(fn))
    sig_msg_list = [
            f"CHECK: {fname}: ld sig: {q.get_double_sig(ld, q.RngState()):.5E}",
            ]
    for msg in sig_msg_list:
        q.displayln_info(msg)

@q.timer_verbose
def auto_contract_meson_corr_psrc(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob):
    fname = q.get_fname()
    fn = f"{job_tag}/auto-contract/traj-{traj}/meson_corr_psrc.lat"
    if get_load_path(fn) is not None:
        return
    cexpr = get_cexpr_meson_corr()
    expr_names = get_expr_names(cexpr)
    total_site = q.Coordinate(get_param(job_tag, "total_site"))
    t_size = total_site[3]
    get_prop = get_get_prop()
    psel_prob = get_psel_prob()
    fsel_prob = get_fsel_prob()
    psel = psel_prob.psel
    fsel = fsel_prob.fsel
    if not fsel.is_containing(psel):
        q.displayln_info(-1, f"WARNING: fsel is not containing psel. The probability weighting may be wrong.")
    fsel_n_elems = fsel.n_elems()
    fsel_prob_arr = fsel_prob[:].ravel()
    psel_prob_arr = psel_prob[:].ravel()
    xg_fsel_arr = fsel.to_psel_local()[:]
    xg_psel_arr = psel[:]
    geo = q.Geometry(total_site, 1)
    total_volume = geo.total_volume()
    def load_data():
        x_t_list = get_mpi_chunk(
                [ (pidx, t_snk,) for t_snk in range(total_site[3]) for pidx in range(len(xg_psel_arr)) ],
                rng_state = None)
        for pidx, t_snk in x_t_list:
            yield pidx, t_snk
    @q.timer
    def feval(args):
        pidx, t_snk = args
        xg_src = tuple(xg_psel_arr[pidx])
        prob_src = psel_prob_arr[pidx]
        t = (xg_src[3] - t_snk) % total_site[3]
        pd = {
                "x_2" : ("point", xg_src,),
                "x_1" : ("wall", t_snk,),
                "size" : total_site,
                }
        val = eval_cexpr(cexpr, positions_dict=pd, get_prop=get_prop)
        return val / prob_src, t
    def sum_function(val_list):
        values = np.zeros((total_site[3], len(expr_names),), dtype=complex)
        for val, t in val_list:
            values[t] += val
        return values.transpose(1, 0)
    auto_contractor_chunk_size = get_param(job_tag, "measurement", "auto_contractor_chunk_size", default=128)
    q.timer_fork(0)
    res_sum = q.glb_sum(
            q.parallel_map_sum(feval, load_data(), sum_function=sum_function, chunksize=auto_contractor_chunk_size))
    q.displayln_info("timer_display for auto_contract_meson_corr_psrc")
    q.timer_display()
    q.timer_merge()
    res_sum *= 1.0 / total_volume
    q.displayln_info(0, res_sum[0])
    ld = q.mk_lat_data([
        [ "expr_name", len(expr_names), expr_names, ],
        [ "t_sep", t_size, [ str(q.rel_mod(t, t_size)) for t in range(t_size) ], ],
        ])
    ld.from_numpy(res_sum)
    ld.save(get_save_path(fn))
    sig_msg_list = [
            f"CHECK: {fname}: ld sig: {q.get_double_sig(ld, q.RngState()):.5E}",
            ]
    for msg in sig_msg_list:
        q.displayln_info(msg)

@q.timer_verbose
def auto_contract_meson_corr_psnk_psrc(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob):
    fname = q.get_fname()
    fn = f"{job_tag}/auto-contract/traj-{traj}/meson_corr_psnk_psrc.lat"
    if get_load_path(fn) is not None:
        return
    cexpr = get_cexpr_meson_corr()
    expr_names = get_expr_names(cexpr)
    total_site = q.Coordinate(get_param(job_tag, "total_site"))
    t_size = total_site[3]
    get_prop = get_get_prop()
    psel_prob = get_psel_prob()
    fsel_prob = get_fsel_prob()
    psel = psel_prob.psel
    fsel = fsel_prob.fsel
    if not fsel.is_containing(psel):
        q.displayln_info(-1, f"WARNING: fsel is not containing psel. The probability weighting may be wrong.")
    fsel_n_elems = fsel.n_elems()
    fsel_prob_arr = fsel_prob[:].ravel()
    psel_prob_arr = psel_prob[:].ravel()
    xg_fsel_arr = fsel.to_psel_local()[:]
    xg_psel_arr = psel[:]
    geo = q.Geometry(total_site, 1)
    total_volume = geo.total_volume()
    r_list = get_r_list(job_tag)
    r_sq_interp_idx_coef_list = get_r_sq_interp_idx_coef_list(job_tag)
    def load_data():
        for pidx in range(len(xg_psel_arr)):
            yield pidx
    @q.timer
    def feval(args):
        pidx = args
        xg_src = tuple(xg_psel_arr[pidx])
        prob_src = psel_prob_arr[pidx]
        res_list = []
        for idx in range(len(xg_fsel_arr)):
            xg_snk = tuple(xg_fsel_arr[idx])
            if xg_snk == xg_src:
                prob_snk = 1.0
            else:
                prob_snk = fsel_prob_arr[idx]
            prob = prob_src * prob_snk
            x_rel = [ q.rel_mod(xg_snk[mu] - xg_src[mu], total_site[mu]) for mu in range(4) ]
            r_sq = q.get_r_sq(x_rel)
            r_idx_low, r_idx_high, coef_low, coef_high = r_sq_interp_idx_coef_list[r_sq]
            t = (xg_snk[3] - xg_src[3]) % total_site[3]
            pd = {
                    "x_2": ("point-snk", xg_snk,),
                    "x_1": ("point", xg_src,),
                    "size": total_site,
                    }
            val = eval_cexpr(cexpr, positions_dict=pd, get_prop=get_prop)
            res_list.append((val / prob, t, r_idx_low, r_idx_high, coef_low, coef_high))
        return res_list
    def sum_function(val_list):
        values = np.zeros((total_site[3], len(r_list), len(expr_names),), dtype=complex)
        for idx, res_list in enumerate(val_list):
            for val, t, r_idx_low, r_idx_high, coef_low, coef_high in res_list:
                values[t, r_idx_low] += coef_low * val
                values[t, r_idx_high] += coef_high * val
            q.displayln_info(f"{fname}: {idx+1}/{len(xg_psel_arr)}")
        return values.transpose(2, 0, 1)
    q.timer_fork(0)
    res_sum = q.glb_sum(
            q.parallel_map_sum(feval, load_data(), sum_function=sum_function, chunksize=1))
    q.displayln_info("timer_display for auto_contract_meson_corr_psnk_psrc")
    q.timer_display()
    q.timer_merge()
    res_sum *= 1.0 / (total_volume**2 / total_site[3])
    q.displayln_info(res_sum[0].sum(1))
    ld = q.mk_lat_data([
        [ "expr_name", len(expr_names), expr_names, ],
        [ "t_sep", t_size, [ str(q.rel_mod(t, t_size)) for t in range(t_size) ], ],
        [ "r", len(r_list), [ f"{r:.5f}" for r in r_list ], ],
        ])
    ld.from_numpy(res_sum)
    ld.save(get_save_path(fn))
    q.displayln_info(f"CHECK: {fname}: ld sig: {q.get_double_sig(ld, q.RngState()):.5E}")

# ----

@q.timer_verbose
def run_job(job_tag, traj):
    fns_produce = [
            f"{job_tag}/auto-contract/traj-{traj}/checkpoint.txt",
            #
            # (f"{job_tag}/prop-rand-u1-light/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-light/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/prop-rand-u1-strange/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-strange/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/prop-rand-u1-charm/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-charm/traj-{traj}/geon-info.txt",),
            #
            (f"{job_tag}/prop-psrc-light/traj-{traj}.qar", f"{job_tag}/prop-psrc-light/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-psrc-light/traj-{traj}.qar", f"{job_tag}/psel-prop-psrc-light/traj-{traj}/checkpoint.txt",),
            (f"{job_tag}/prop-psrc-strange/traj-{traj}.qar", f"{job_tag}/prop-psrc-strange/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-psrc-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-psrc-strange/traj-{traj}/checkpoint.txt",),
            #
            # (f"{job_tag}/prop-smear-light/traj-{traj}.qar", f"{job_tag}/prop-smear-light/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/psel-prop-smear-light/traj-{traj}.qar", f"{job_tag}/psel-prop-smear-light/traj-{traj}/checkpoint.txt",),
            # (f"{job_tag}/prop-smear-strange/traj-{traj}.qar", f"{job_tag}/prop-smear-strange/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/psel-prop-smear-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-smear-strange/traj-{traj}/checkpoint.txt",),
            #
            (f"{job_tag}/prop-wsrc-light/traj-{traj}.qar", f"{job_tag}/prop-wsrc-light/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-wsrc-light/traj-{traj}.qar", f"{job_tag}/psel-prop-wsrc-light/traj-{traj}/checkpoint.txt",),
            (f"{job_tag}/prop-wsrc-strange/traj-{traj}.qar", f"{job_tag}/prop-wsrc-strange/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-wsrc-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-wsrc-strange/traj-{traj}/checkpoint.txt",),
            ]
    if job_tag[:5] == "test-":
        fns_need = []
    else:
        fns_need = [
                (f"{job_tag}/configs/ckpoint_lat.{traj}", f"{job_tag}/configs/ckpoint_lat.IEEE64BIG.{traj}",),
                f"{job_tag}/eig/traj-{traj}/metadata.txt",
                # f"{job_tag}/gauge-transform/traj-{traj}.field",
                # f"{job_tag}/point-selection/traj-{traj}.txt",
                # f"{job_tag}/field-selection/traj-{traj}.field",
                # f"{job_tag}/wall-src-info-light/traj-{traj}.txt",
                # f"{job_tag}/wall-src-info-strange/traj-{traj}.txt",
                ]
    if not check_job(job_tag, traj, fns_produce, fns_need):
        return
    #
    traj_gf = traj
    if job_tag[:5] == "test-":
        # ADJUST ME
        traj_gf = 1000
        #
    #
    get_gf = run_gf(job_tag, traj_gf)
    get_gt = run_gt(job_tag, traj_gf, get_gf)
    get_gf_ape = run_gf_ape(job_tag, get_gf)
    #
    get_wi = run_wi(job_tag, traj)
    #
    get_eig_light = run_eig(job_tag, traj_gf, get_gf)
    get_eig_strange = run_eig_strange(job_tag, traj_gf, get_gf)
    #
    def run_wsrc_full():
        get_eig = get_eig_light
        # run_get_inverter(job_tag, traj, inv_type=0, get_gf=get_gf, get_gt=get_gt, get_eig=get_eig)
        run_prop_wsrc_full(job_tag, traj, inv_type=0, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_wi=get_wi)
        q.clean_cache(q.cache_inv)
        #
        get_eig = get_eig_strange
        # run_get_inverter(job_tag, traj, inv_type=1, get_gf=get_gf, get_gt=get_gt, get_eig=get_eig)
        run_prop_wsrc_full(job_tag, traj, inv_type=1, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_wi=get_wi)
        q.clean_cache(q.cache_inv)
    #
    run_wsrc_full()
    #
    get_fsel, get_psel, get_fsel_prob, get_psel_prob, get_f_rand_01 = run_fsel_psel_from_wsrc_prop_full(job_tag, traj, get_wi=get_wi)
    #
    if get_fsel is None:
        q.clean_cache()
        return
    #
    get_fselc = run_fselc(job_tag, traj, get_fsel, get_psel)
    #
    run_prop_wsrc_sparse(job_tag, traj, inv_type=0, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fsel, get_wi=get_wi)
    run_prop_wsrc_sparse(job_tag, traj, inv_type=1, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fsel, get_wi=get_wi)
    #
    get_psel_smear = run_psel_smear(job_tag, traj)
    #
    def run_with_eig():
        get_eig = get_eig_light
        # run_get_inverter(job_tag, traj, inv_type=0, get_gf=get_gf, get_eig=get_eig)
        # run_prop_wsrc(job_tag, traj, inv_type=0, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_wi=get_wi)
        # run_prop_rand_u1(job_tag, traj, inv_type=0, get_gf=get_gf, get_fsel=get_fsel, get_eig=get_eig)
        run_prop_psrc(job_tag, traj, inv_type=0, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_f_rand_01=get_f_rand_01)
        # run_prop_smear(job_tag, traj, inv_type=0, get_gf=get_gf, get_gf_ape=get_gf_ape, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_psel_smear=get_psel_smear)
        q.clean_cache(q.cache_inv)
    #
    def run_with_eig_strange():
        get_eig = get_eig_strange
        # run_get_inverter(job_tag, traj, inv_type=1, get_gf=get_gf, get_eig=get_eig)
        # run_prop_wsrc(job_tag, traj, inv_type=1, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_wi=get_wi)
        # run_prop_rand_u1(job_tag, traj, inv_type=1, get_gf=get_gf, get_fsel=get_fsel, get_eig=get_eig)
        run_prop_psrc(job_tag, traj, inv_type=1, get_gf=get_gf, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_f_rand_01=get_f_rand_01)
        # run_prop_smear(job_tag, traj, inv_type=1, get_gf=get_gf, get_gf_ape=get_gf_ape, get_eig=get_eig, get_gt=get_gt, get_psel=get_psel, get_fsel=get_fselc, get_psel_smear=get_psel_smear)
        q.clean_cache(q.cache_inv)
    #
    def run_charm():
        # run_get_inverter(job_tag, traj, inv_type=2, get_gf=get_gf)
        # run_prop_rand_u1(job_tag, traj, inv_type=2, get_gf=get_gf, get_fsel=get_fsel)
        q.clean_cache(q.cache_inv)
    #
    run_with_eig()
    run_with_eig_strange()
    run_charm()
    #
    get_get_prop = run_get_prop(job_tag, traj,
            get_gf=get_gf,
            get_gt=get_gt,
            get_psel=get_psel,
            get_fsel=get_fsel,
            get_psel_smear=get_psel_smear,
            get_wi=get_wi,
            prop_types=[
                "wsrc psel s",
                "wsrc psel l",
                "wsrc fsel s",
                "wsrc fsel l",
                "psrc psel s",
                "psrc psel l",
                "psrc fsel s",
                "psrc fsel l",
                # "rand_u1 fsel c",
                # "rand_u1 fsel s",
                # "rand_u1 fsel l",
                ],
            )
    #
    run_r_list(job_tag)
    #
    fn_checkpoint_auto_contract = f"{job_tag}/auto-contract/traj-{traj}/checkpoint.txt"
    #
    if job_tag == "64I":
        q.qtouch_info(get_save_path(fn_checkpoint_auto_contract))
        q.sync_node()
    #
    fns_produce_auto_contract = [
            fn_checkpoint_auto_contract,
            ]
    fns_need_auto_contract = [
            # (f"{job_tag}/prop-rand-u1-light/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-light/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/prop-rand-u1-strange/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-strange/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/prop-rand-u1-charm/traj-{traj}.qar", f"{job_tag}/prop-rand-u1-charm/traj-{traj}/geon-info.txt",),
            #
            (f"{job_tag}/prop-psrc-light/traj-{traj}.qar", f"{job_tag}/prop-psrc-light/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-psrc-light/traj-{traj}.qar", f"{job_tag}/psel-prop-psrc-light/traj-{traj}/checkpoint.txt",),
            (f"{job_tag}/prop-psrc-strange/traj-{traj}.qar", f"{job_tag}/prop-psrc-strange/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-psrc-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-psrc-strange/traj-{traj}/checkpoint.txt",),
            #
            # (f"{job_tag}/prop-smear-light/traj-{traj}.qar", f"{job_tag}/prop-smear-light/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/psel-prop-smear-light/traj-{traj}.qar", f"{job_tag}/psel-prop-smear-light/traj-{traj}/checkpoint.txt",),
            # (f"{job_tag}/prop-smear-strange/traj-{traj}.qar", f"{job_tag}/prop-smear-strange/traj-{traj}/geon-info.txt",),
            # (f"{job_tag}/psel-prop-smear-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-smear-strange/traj-{traj}/checkpoint.txt",),
            #
            (f"{job_tag}/prop-wsrc-light/traj-{traj}.qar", f"{job_tag}/prop-wsrc-light/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-wsrc-light/traj-{traj}.qar", f"{job_tag}/psel-prop-wsrc-light/traj-{traj}/checkpoint.txt",),
            (f"{job_tag}/prop-wsrc-strange/traj-{traj}.qar", f"{job_tag}/prop-wsrc-strange/traj-{traj}/geon-info.txt",),
            (f"{job_tag}/psel-prop-wsrc-strange/traj-{traj}.qar", f"{job_tag}/psel-prop-wsrc-strange/traj-{traj}/checkpoint.txt",),
            ]
    if not check_job(job_tag, traj, fns_produce_auto_contract, fns_need_auto_contract):
        return
    if q.obtain_lock(f"locks/{job_tag}-{traj}-auto-contract"):
        get_prop = get_get_prop()
        if get_prop is not None:
            q.timer_fork()
            # ADJUST ME
            auto_contract_meson_corr(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob)
            auto_contract_meson_corr_psnk(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob)
            auto_contract_meson_corr_psrc(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob)
            auto_contract_meson_corr_psnk_psrc(job_tag, traj, get_get_prop, get_psel_prob, get_fsel_prob)
            #
            q.qtouch_info(get_save_path(fn_checkpoint_auto_contract))
            q.displayln_info("timer_display for runjob")
            q.timer_display()
            q.timer_merge()
        q.release_lock()
    q.clean_cache()

def get_all_cexpr():
    benchmark_eval_cexpr(get_cexpr_meson_corr())

set_param("test-4nt8", "mk_sample_gauge_field", "rand_n_step", value=2)
set_param("test-4nt8", "mk_sample_gauge_field", "flow_n_step", value=8)
set_param("test-4nt8", "mk_sample_gauge_field", "hmc_n_traj", value=1)
set_param("test-4nt8", "fermion_params", 0, 2, "Ls", value=8)
set_param("test-4nt8", "fermion_params", 1, 2, "Ls", value=8)
set_param("test-4nt8", "fermion_params", 2, 2, "Ls", value=8)
set_param("test-4nt8", "cg_params-0-0", "maxiter", value=5)
set_param("test-4nt8", "cg_params-0-1", "maxiter", value=5)
set_param("test-4nt8", "cg_params-0-2", "maxiter", value=5)
set_param("test-4nt8", "cg_params-1-0", "maxiter", value=5)
set_param("test-4nt8", "cg_params-1-1", "maxiter", value=5)
set_param("test-4nt8", "cg_params-1-2", "maxiter", value=5)
set_param("test-4nt8", "cg_params-0-0", "maxcycle", value=1)
set_param("test-4nt8", "cg_params-0-1", "maxcycle", value=2)
set_param("test-4nt8", "cg_params-0-2", "maxcycle", value=3)
set_param("test-4nt8", "cg_params-1-0", "maxcycle", value=1)
set_param("test-4nt8", "cg_params-1-1", "maxcycle", value=2)
set_param("test-4nt8", "cg_params-1-2", "maxcycle", value=3)
set_param("test-4nt8", "cg_params-0-2", "pv_maxiter", value=5)
set_param("test-4nt8", "cg_params-1-2", "pv_maxiter", value=5)
set_param("test-4nt8", "trajs", value=[ 1000, ])
set_param("test-8nt16", "trajs", value=[ 1000, 2000, ])
set_param("24D", "lanc_params", 1, value=None)
set_param("24D", "clanc_params", 1, value=None)
set_param("24D", 'fermion_params', 0, 2, value=deepcopy(get_param("24D", 'fermion_params', 0, 0)))
set_param("24D", 'fermion_params', 1, 0, value=deepcopy(get_param("24D", 'fermion_params', 1, 2)))
set_param("24D", 'fermion_params', 1, 1, value=deepcopy(get_param("24D", 'fermion_params', 1, 2)))
set_param("64I", "trajs", value=list(range(1200, 3680, 40)))

qg.begin_with_gpt()

job_tags_default = [
        "test-4nt8",
        # "test-8nt16",
        # "24D",
        # "64I",
        ]

job_tags = q.get_arg("--job_tags", default="").split(",")

if job_tags == [ "", ]:
    job_tags = job_tags_default
else:
    is_cython = True

q.check_time_limit()

get_all_cexpr()

for job_tag in job_tags:
    q.displayln_info(pprint.pformat(get_param(job_tag)))
    for v in get_param(job_tag).items():
        q.displayln_info(f"CHECK: {v}")
    if not q.does_file_exist_qar_sync_node(get_save_path(f"{job_tag}/params.pickle")):
        q.save_pickle_obj(get_param(job_tag), get_save_path(f"{job_tag}/params.pickle"), is_sync_node=True)
    if not q.does_file_exist_qar_sync_node(get_save_path(f"{job_tag}/params.txt")):
        q.qtouch_info(get_save_path(f"{job_tag}/params.txt"), pprint.pformat(get_param(job_tag)))
    for traj in get_param(job_tag, "trajs"):
        run_job(job_tag, traj)

q.timer_display()

qg.end_with_gpt()

q.displayln_info("CHECK: finished successfully.")
