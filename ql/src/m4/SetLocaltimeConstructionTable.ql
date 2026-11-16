/**
 * @name setLocaltime complete source construction table
 * @description Source shape only; not runtime target, reachability, or safety.
 * @id ucode/m4/setlocaltime-construction-table
 * @tags testing
 */
import codeql.ucode.m4.SetLocaltimeConstruction

from UCODE::Program p, UCODE::FunctionExpression fn, UCODE::CallExpression initializer,
  UCODE::MemberExpression input, UCODE::Identifier guard, UCODE::CallExpression formatter,
  UCODE::String format, UCODE::CallExpression sink, UCODE::MemberExpression field,
  int i, string name, string conv,
  int z00, int z01, int z02, int z03, int z10, int z11, int z12, int z13, int z20, int z21, int z22, int z23, int z30, int z31, int z32, int z33, int z40, int z41, int z42, int z43, int z50, int z51, int z52, int z53, int z60, int z61, int z62, int z63, int z70, int z71, int z72, int z73
where
  p.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  construction(p, fn, initializer, input, guard, formatter, format, sink) and
  locations_default(field.getLocation(), _, z70, z71, z72, z73) and
  locations_default(sink.getLocation(), _, z60, z61, z62, z63) and
  locations_default(format.getLocation(), _, z50, z51, z52, z53) and
  locations_default(formatter.getLocation(), _, z40, z41, z42, z43) and
  locations_default(guard.getLocation(), _, z30, z31, z32, z33) and
  locations_default(input.getLocation(), _, z20, z21, z22, z23) and
  locations_default(initializer.getLocation(), _, z10, z11, z12, z13) and
  locations_default(fn.getLocation(), _, z00, z01, z02, z03) and
  slot(i, name, conv) and field = formatter.getArguments().getChild(i)
select "setlocaltime_complete_decimal_datetime_source_v1" as observation_kind,
  "luci" as ubus_object,
  "setLocaltime" as method,
  p.getLocation().getFile().getRelativePath() as source_path,
  "t" as local_name,
  "date -s \"%04d-%02d-%02d %02d:%02d:%02d\" >/dev/null" as format_value,
  z00 as callback_start_line,
  z01 as callback_start_column,
  z02 as callback_end_line,
  z03 as callback_end_column,
  z10 as initializer_start_line,
  z11 as initializer_start_column,
  z12 as initializer_end_line,
  z13 as initializer_end_column,
  z20 as input_start_line,
  z21 as input_start_column,
  z22 as input_end_line,
  z23 as input_end_column,
  z30 as guard_start_line,
  z31 as guard_start_column,
  z32 as guard_end_line,
  z33 as guard_end_column,
  z40 as formatter_start_line,
  z41 as formatter_start_column,
  z42 as formatter_end_line,
  z43 as formatter_end_column,
  z50 as format_start_line,
  z51 as format_start_column,
  z52 as format_end_line,
  z53 as format_end_column,
  z60 as sink_start_line,
  z61 as sink_start_column,
  z62 as sink_end_line,
  z63 as sink_end_column,
  i as slot_index,
  conv as conversion,
  name as field_name,
  z70 as field_start_line,
  z71 as field_start_column,
  z72 as field_end_line,
  z73 as field_end_column
