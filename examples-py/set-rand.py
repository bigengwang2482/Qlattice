#!/usr/bin/env python3

import sys
import qlat as q

size_node_list = [
        [1, 1, 1, 1],
        [1, 1, 1, 2],
        [1, 1, 1, 4],
        [1, 1, 1, 8],
        [2, 2, 2, 2],
        [2, 2, 2, 4],
        ]

q.begin(sys.argv, size_node_list)

q.qremove_all_info("results")
q.qmkdir_info("results")

rs = q.RngState("seed")
rs_prop = rs.split("prop")

total_site = [ 4, 4, 4, 8, ]
geo = q.Geometry(total_site, 1)

q.displayln_info(f"CHECK: total_site = {total_site}")
q.displayln_info(f"CHECK: geo = {geo}")

prop = q.Prop(geo)
prop.set_rand(rs_prop, 1.0, 0.0)
q.displayln_info(f"CHECK: prop.crc32() = {prop.crc32()} ; prop.qnorm() = {prop.qnorm():.15E}")

n_points = 16
psel = q.PointSelection()
psel.set_rand(rs.split("psel"), total_site, n_points)

n_per_tslice = 16
fsel = q.FieldSelection(geo.total_site(), n_per_tslice, rs.split("fsel"))

fselc = fsel.copy()
fselc.add_psel(psel)

sc_prop = q.SelProp(fselc)
sc_prop @= prop
q.displayln_info(f"CHECK: sc_prop.qnorm() = {sc_prop.qnorm():.15E}")

sc_prop1 = q.SelProp(fselc)
sc_prop1.set_rand(rs_prop, 1.0, 0.0)
sc_prop1 -= sc_prop
q.displayln_info(f"CHECK: sc_prop1.qnorm() = {sc_prop1.qnorm():.15E}")

s_prop = q.SelProp(fsel)
s_prop @= prop
q.displayln_info(f"CHECK: s_prop.qnorm() = {s_prop.qnorm():.15E}")

s_prop1 = q.SelProp(fsel)
s_prop1.set_rand(rs_prop, 1.0, 0.0)
s_prop1 -= s_prop
q.displayln_info(f"CHECK: s_prop1.qnorm() = {s_prop1.qnorm():.15E}")

s_prop2 = q.SelProp(fsel)
s_prop2 @= sc_prop
s_prop2 -= s_prop
q.displayln_info(f"CHECK: s_prop2.qnorm() = {s_prop2.qnorm():.15E}")

sp_prop = q.PselProp(psel)
sp_prop @= prop
q.displayln_info(f"CHECK: sp_prop.qnorm() = {sp_prop.qnorm():.15E}")

sp_prop1 = q.PselProp(psel)
sp_prop1 @= sc_prop
sp_prop1 -= sp_prop
q.displayln_info(f"CHECK: sp_prop1.qnorm() = {sp_prop1.qnorm():.15E}")

prop_norm = q.sqrt_double_field(q.qnorm_field(prop))
q.displayln_info(f"CHECK: prop_norm.qnorm() = {prop_norm.qnorm():.15E}")

s_prop_norm = q.sqrt_double_field(q.qnorm_field(s_prop))
q.displayln_info(f"CHECK: s_prop_norm.qnorm() = {s_prop_norm.qnorm():.15E}")

s_prop_norm1 = q.SelectedField("Double", fsel)
s_prop_norm1 @= prop_norm
s_prop_norm1 -= s_prop_norm
q.displayln_info(f"CHECK: s_prop_norm1.qnorm() = {s_prop_norm1.qnorm():.15E}")

sp_prop_norm = q.sqrt_double_field(q.qnorm_field(sp_prop))
q.displayln_info(f"CHECK: sp_prop_norm.qnorm() = {sp_prop_norm.qnorm():.15E}")

sp_prop_norm1 = q.SelectedPoints("Double", psel)
sp_prop_norm1 @= prop_norm
sp_prop_norm1 -= sp_prop_norm
q.displayln_info(f"CHECK: sp_prop_norm1.qnorm() = {sp_prop_norm1.qnorm():.15E}")

q.timer_display()

q.displayln_info(f"CHECK: finished successfully.")

q.end()
