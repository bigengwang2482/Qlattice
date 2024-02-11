#!/usr/bin/env python3

import qlat as q
import os

q.begin_with_mpi()

q.qremove_all_info("results")
q.qmkdir_info("results")
rs = q.RngState("seed")
total_site = q.Coordinate([4, 4, 4, 8])
geo = q.Geometry(total_site, 1)
q.displayln_info("CHECK: geo.show() =", geo.show())

psel = q.PointsSelection([[0,0,0,0], [0,1,2,0]])
n_per_tslice = 16
fsel = q.FieldSelection()
fsel.set_rand(geo.total_site(), n_per_tslice, rs.split("fsel"))

fselc = fsel.copy()
fselc.add_psel(psel)

prop = q.Prop(geo)
prop.set_rand(rs.split("prop-1"))
q.displayln_info("CHECK: prop", prop.crc32(), f"{prop.qnorm():.14E}")

sfw = q.open_fields("results/prop.fields", "w", q.Coordinate([ 1, 1, 1, 8, ]))

sf_list = sorted(q.show_all_shuffled_fields_writer())
q.sync_node()
q.displayln_info(f"CHECK: q.show_all_shuffled_fields_writer()")
for idx, s in enumerate(sf_list):
    q.displayln_info(f"CHECK: {idx} {s}")
q.sync_node()

sq_list = sorted(q.show_all_qfile())
q.sync_node()
q.displayln_info(f"CHECK: q.show_all_qfile()")
for idx, s in enumerate(sq_list):
    q.displayln_info(f"CHECK: {idx} {s}")
q.sync_node()

q.displayln_info("CHECK: sfw.new_size_node()", sfw.new_size_node())

prop.save_double(sfw, "prop.d")

prop.save_float_from_double(sfw, "prop")

sfw.flush()

s_prop = q.SelProp(fsel)
s_prop @= prop
q.displayln_info("CHECK: s_prop = SelProp(fsel) and s_prop @= prop", f"{s_prop.qnorm():14E}")
s_prop.save_float_from_double(sfw, "s_prop")

prop1 = q.SelProp(fselc)
prop1 @= prop
q.displayln_info("CHECK: prop1 = SelProp(fselc) and prop1 @= prop", f"{prop1.qnorm():.14E}")
prop1.save_float_from_double(sfw, "prop1")

sfw.close()

sfr = q.open_fields("results/prop.fields", "r")

sq_list = sorted(q.show_all_qfile())
q.sync_node()
q.displayln_info(f"CHECK: q.show_all_qfile()")
for idx, s in enumerate(sq_list):
    q.displayln_info(f"CHECK: {idx} {s}")
q.sync_node()

fns = sfr.list()

q.displayln_info("CHECK: sfr.list()", sfr.list())

q.displayln_info("CHECK: sfr.new_size_node()", sfr.new_size_node())

prop_d = q.Prop()
prop_d.load_double(sfr, "prop.d")
q.displayln_info("CHECK: prop_d", prop_d.crc32(), f"{prop_d.qnorm():.14E}")
prop_d -= prop
q.displayln_info("CHECK: prop_d -= prop", prop_d.crc32(), f"{prop_d.qnorm():.14E}")

prop_f = q.Prop()
prop_f.load_double_from_float(sfr, "prop")
q.displayln_info("CHECK: prop_f", prop_f.crc32(), f"{prop_f.qnorm():.14E}")
prop_f -= prop
q.displayln_info("CHECK: prop_f -= prop", prop_f.crc32(), f"{prop_f.qnorm():.14E}")

s_prop_f = q.SelProp(fsel)
s_prop_f.load_double_from_float(sfr, "s_prop")
q.displayln_info("CHECK: s_prop_f", f"{s_prop_f.qnorm():.14E}")
s_prop_f -= s_prop
q.displayln_info("CHECK: s_prop_f -= s_prop", f"{s_prop_f.qnorm():.14E}")

prop1_f = q.SelProp(fselc)
prop1_f.load_double_from_float(sfr, "prop1")
q.displayln_info("CHECK: prop1_f", f"{prop1_f.qnorm():.14E}")
prop1_f -= prop1
q.displayln_info("CHECK: prop1_f -= prop1", f"{prop1_f.qnorm():.14E}")

prop1_ff = q.SelProp(None)
prop1_ff.load_double_from_float(sfr, "prop1")
q.displayln_info("CHECK: prop1_ff", f"{prop1_ff.qnorm():.14E}")
assert q.is_matching_fsel(prop1_ff.fsel, fselc)
prop1_ff -= prop1
q.displayln_info("CHECK: prop1_ff -= prop1", f"{prop1_f.qnorm():.14E}")

sfr.close()

q.displayln_info("CHECK: ", q.list_fields("results/prop.fields"))

q.properly_truncate_fields("results/prop.fields")

q.displayln_info("CHECK: ", q.list_fields("results/prop.fields"))

q.truncate_fields("results/prop.fields", fns)

q.displayln_info("CHECK: ", q.list_fields("results/prop.fields"))

q.truncate_fields("results/prop.fields", fns[:-1])

q.displayln_info("CHECK: ", q.list_fields("results/prop.fields"))

q.truncate_fields("results/prop.fields", [])

q.displayln_info("CHECK: ", q.list_fields("results/prop.fields"))

q.displayln_info("CHECK: ", q.qls_all_sync_node("results"))

q.timer_display()

q.end_with_mpi()

q.displayln_info(f"CHECK: finished successfully.")
