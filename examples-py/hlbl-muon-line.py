#!/usr/bin/env python3

json_results = []

import qlat as q
import numpy as np

epsabs = 1e-8
epsrel = 1e-3
mineval = 1024 * 1024
maxeval = 1024 * 1024 * 1024

eps0 = (epsabs * 1e2, epsrel * 1e2, mineval // 1024, maxeval // 1024,)
eps1 = (epsabs * 1e1, epsrel * 1e1, mineval, maxeval,)
eps2 = (epsabs, epsrel, mineval, maxeval,)
eps3 = (epsabs / 1e1, epsrel / 1e1, mineval, maxeval,)

eps = eps2

def load_or_compute_muon_line_interpolation():
    path = f"results/muon-line-interpolation-data"
    if not q.does_file_exist_qar_sync_node(f"{path}.qar"):
        q.compute_save_muonline_interpolation(
                f"{path}/{0:010d}",
                [ 3, 2, 2, 2, 2, ],
                eps0)
        q.compute_save_muonline_interpolation(
                f"{path}/{1:010d}",
                [ 2, 2, 2, 2, 2, ],
                eps0)
        q.qar_create_info(f"{path}.qar", path, is_remove_folder_after=True)
    q.sync_node();
    q.load_multiple_muonline_interpolations("results/muon-line-interpolation-data", [ 0, 1, ])

q.begin_with_mpi()

has_cuba = q.has_cuba()

q.displayln_info(f"CHECK: has_cuba={has_cuba}")

if not has_cuba:
    q.displayln_info(f"CHECK: quit due to not having CUBA.")
    q.end_with_mpi()
    exit()

q.test_integration_multi_dimensional()

load_or_compute_muon_line_interpolation()

cx = q.Coordinate([ 1, 2, 3, 4, ])
cy = q.Coordinate([ 3, 1, 2, 1, ])
cz = q.Coordinate([ 0, 0, 0, 0, ])
total_site = q.Coordinate([ 16, 16, 16, 32, ])
muon_mass = 0.4

c1 = q.CoordinateD([ 1, 2, 3, 4, ]) * 0.4
c2 = q.CoordinateD([ 3, 1, 2, 1, ]) * 0.4
c3 = q.CoordinateD([ 0, 0, 0, 0, ]) * 0.4

q.displayln_info(0, f"{c1, c2, c3}")

ve = None

if True:
    fname = "calc_muon_line_m"
    v0 = q.calc_muon_line_m(c1, c2, eps1)
    json_results.append((f"{fname}: v0 sig", q.get_double_sig(v0, q.RngState()),))
    v1 = q.calc_muon_line_m(c1, c2, eps2)
    json_results.append((f"{fname}: v1 sig", q.get_double_sig(v1, q.RngState()),))
    ve = v1
    q.displayln_info(np.sqrt(q.qnorm(v0 - ve) / q.qnorm(ve)))
    if False:
        v2 = q.calc_muon_line_m(c1, c2, eps3)
        json_results.append((f"{fname}: v2 sig", q.get_double_sig(v2, q.RngState()),))
        ve = v2
        q.displayln_info(np.sqrt(q.qnorm(v0 - ve) / q.qnorm(ve)))
        q.displayln_info(np.sqrt(q.qnorm(v1 - ve) / q.qnorm(ve)))


if True:
    fname = "get_muon_line_m"
    load_or_compute_muon_line_interpolation()
    for idx in [ 0, 1, ]:
        vv1 = q.get_muon_line_m(c1, c2, c3, idx, eps)
        json_results.append((f"{fname}: {idx} vv1 sig", q.get_double_sig(vv1, q.RngState()),))
        vv2 = q.get_muon_line_m(c2, c3, c1, idx, eps)
        json_results.append((f"{fname}: {idx} vv2 sig", q.get_double_sig(vv2, q.RngState()),))
        vv3 = q.get_muon_line_m(c3, c1, c2, idx, eps)
        json_results.append((f"{fname}: {idx} vv3 sig", q.get_double_sig(vv3, q.RngState()),))
        vv4 = q.get_muon_line_m(c3, c2, c1, idx, eps)
        json_results.append((f"{fname}: {idx} vv4 sig", q.get_double_sig(vv4, q.RngState()),))
        vv5 = q.get_muon_line_m(c2, c1, c3, idx, eps)
        json_results.append((f"{fname}: {idx} vv5 sig", q.get_double_sig(vv5, q.RngState()),))
        vv6 = q.get_muon_line_m(c1, c3, c2, idx, eps)
        json_results.append((f"{fname}: {idx} vv6 sig", q.get_double_sig(vv6, q.RngState()),))
        q.displayln_info(np.sqrt(q.qnorm(vv1)))
        q.displayln_info(np.sqrt(q.qnorm(vv1 - ve)))
    q.clear_muon_line_interpolations()

if True:
    fname = "get_muon_line_m_extra"
    weights = q.get_muon_line_m_extra_weights()
    for idx, ws in enumerate(weights):
        q.displayln_info(f"{fname}: initial weights {idx} {ws}")
        json_results.append((f"{fname}: initial weights {idx}", q.get_double_sig(np.array(ws), q.RngState()),))
    q.set_muon_line_m_extra_weights([ [ 4/3, -1/3, ], [ 1.0, ], ])
    weights = q.get_muon_line_m_extra_weights()
    for idx, ws in enumerate(weights):
        q.displayln_info(f"{fname}: set weights {idx} {ws}")
        json_results.append((f"{fname}: set weights {idx}", q.get_double_sig(np.array(ws), q.RngState()),))
    q.set_muon_line_m_extra_weights()
    weights = q.get_muon_line_m_extra_weights()
    for idx, ws in enumerate(weights):
        q.displayln_info(f"{fname}: default weights {idx} {ws}")
        json_results.append((f"{fname}: default weights {idx}", q.get_double_sig(np.array(ws), q.RngState()),))
    load_or_compute_muon_line_interpolation()
    q.set_muon_line_m_extra_weights([ [ 4/3, -1/3, ], [ 1.0, ], ])
    for tag in [ 0, 1, ]:
        vv1 = q.get_muon_line_m_extra(c1, c2, c3, tag)
        json_results.append((f"{fname}: tag={tag} vv1 sig", q.get_double_sig(vv1, q.RngState()),))
        vv2 = q.get_muon_line_m_extra(c2, c3, c1, tag)
        json_results.append((f"{fname}: tag={tag} vv2 sig", q.get_double_sig(vv2, q.RngState()),))
        vv3 = q.get_muon_line_m_extra(c3, c1, c2, tag)
        json_results.append((f"{fname}: tag={tag} vv3 sig", q.get_double_sig(vv3, q.RngState()),))
        vv4 = q.get_muon_line_m_extra(c3, c2, c1, tag)
        json_results.append((f"{fname}: tag={tag} vv4 sig", q.get_double_sig(vv4, q.RngState()),))
        vv5 = q.get_muon_line_m_extra(c2, c1, c3, tag)
        json_results.append((f"{fname}: tag={tag} vv5 sig", q.get_double_sig(vv5, q.RngState()),))
        vv6 = q.get_muon_line_m_extra(c1, c3, c2, tag)
        json_results.append((f"{fname}: tag={tag} vv6 sig", q.get_double_sig(vv6, q.RngState()),))
    q.clear_muon_line_interpolations()

def test_get_muon_line_m_extra_lat(total_site, muon_mass, tag, rng_seed):
    fname = q.get_fname()
    rng = q.RngState(rng_seed)
    cx = rng.c_rand_gen(total_site)
    cy = rng.c_rand_gen(total_site)
    cz = rng.c_rand_gen(total_site)
    vv1 = q.get_muon_line_m_extra_lat(cx, cy, cz, total_site, muon_mass, tag)
    vv2 = q.get_muon_line_m_extra_lat(cy, cz, cx, total_site, muon_mass, tag)
    vv3 = q.get_muon_line_m_extra_lat(cz, cx, cy, total_site, muon_mass, tag)
    vv4 = q.get_muon_line_m_extra_lat(cz, cy, cx, total_site, muon_mass, tag)
    vv5 = q.get_muon_line_m_extra_lat(cy, cx, cz, total_site, muon_mass, tag)
    vv6 = q.get_muon_line_m_extra_lat(cx, cz, cy, total_site, muon_mass, tag)
    vv_all = np.stack([ vv1, vv2, vv3, vv4, vv5, vv6, ])
    json_results.append((f"{fname}: {total_site} {muon_mass} {tag} {rng_seed} {[ cx, cy, cz, ]}", q.get_double_sig(vv_all, q.RngState()),))

if True:
    fname = "get_muon_line_m_extra_lat"
    load_or_compute_muon_line_interpolation()
    q.set_muon_line_m_extra_weights([ [ 4/3, -1/3, ], [ 1.0, ], ])
    for tag in [ 0, 1, ]:
        vv1 = q.get_muon_line_m_extra_lat(cx, cy, cz, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv1 sig", q.get_double_sig(vv1, q.RngState()),))
        vv2 = q.get_muon_line_m_extra_lat(cy, cz, cx, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv2 sig", q.get_double_sig(vv2, q.RngState()),))
        vv3 = q.get_muon_line_m_extra_lat(cz, cx, cy, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv3 sig", q.get_double_sig(vv3, q.RngState()),))
        vv4 = q.get_muon_line_m_extra_lat(cz, cy, cx, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv4 sig", q.get_double_sig(vv4, q.RngState()),))
        vv5 = q.get_muon_line_m_extra_lat(cy, cx, cz, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv5 sig", q.get_double_sig(vv5, q.RngState()),))
        vv6 = q.get_muon_line_m_extra_lat(cx, cz, cy, total_site, muon_mass, tag)
        json_results.append((f"{fname}: tag={tag} vv6 sig", q.get_double_sig(vv6, q.RngState()),))
    for total_site in [
        q.Coordinate([ 3, 3, 3, 3, ]),
        q.Coordinate([ 3, 3, 3, 7, ]),
        q.Coordinate([ 2, 3, 4, 5, ]),
        q.Coordinate([ 4, 3, 2, 5, ]),
        q.Coordinate([ 4, 4, 4, 8, ]),
        ]:
        for muon_mass in [ 0.1, 0.4, ]:
            for tag in [ 0, 1, ]:
                for rng_seed in range(4):
                    test_get_muon_line_m_extra_lat(total_site, muon_mass, tag, rng_seed)
    q.clear_muon_line_interpolations()

check_eps = 1e-5

if 0 == q.get_id_node():
    import os
    json_fn_name = os.path.splitext(__file__)[0] + ".log.json"
    q.qtouch(json_fn_name + ".new", q.json_dumps(json_results, indent=1))
    if q.does_file_exist_qar(json_fn_name):
        json_results_load = q.json_loads(q.qcat(json_fn_name))
        for i, pl in enumerate(json_results_load):
            p = json_results[i]
            nl, vl = pl
            n, v = p
            if n != nl:
                q.displayln(f"CHECK: {i} {p} load:{pl}")
                q.displayln("CHECK: ERROR: JSON results item does not match.")
            if abs(v - vl) > check_eps * (abs(v) + abs(vl)):
                q.displayln(f"CHECK: {i} {p} load:{pl}")
                q.displayln("CHECK: ERROR: JSON results value does not match.")
        if len(json_results) != len(json_results_load):
            q.displayln(f"CHECK: len(json_results)={len(json_results)} load:{len(json_results_load)}")
            q.displayln("CHECK: ERROR: JSON results len does not match.")

q.timer_display()

q.end_with_mpi()

q.displayln_info("CHECK: finished successfully.")
