/**
 * @name getBlockDevices literal popen source observation
 * @description Stable table of syntactic callback-body observations; no reachability or authorization claim.
 * @id ucode/m4/get-block-devices-effect-table
 * @tags testing
 */

import codeql.ucode.m3.Models

from UCODE::CallExpression c, UCODE::ImportStatement imp
where
  c.getLocation().getFile().getBaseName() = "luci" and
  c.getFunction().(UCODE::Identifier).getValue() = "popen" and
  imp.getLocation().getFile() = c.getLocation().getFile() and
  namedImport(imp, "fs", "popen") and
  c.getParent*() = rpcCallFn("getBlockDevices") and
  stringLiteralValue(c.getArguments().getChild(0).(UCODE::String)) =
    "/sbin/block info 2>/dev/null"
select "callback_body_call" as observation_kind,
  "getBlockDevices" as method,
  "popen" as sink_kind,
  "/sbin/block info 2>/dev/null" as command,
  c.getLocation().getFile().getRelativePath() as source_path,
  c.getLocation().getStartLine() as start_line,
  c.getLocation().getStartColumn() as start_column,
  c.getLocation().getEndLine() as end_line,
  c.getLocation().getEndColumn() as end_column
