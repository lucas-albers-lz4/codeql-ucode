/**
 * @name setBlockDetect literal system source observation
 * @description Stable table of syntactic callback-body observations; no reachability or authorization claim.
 * @id ucode/m4/set-block-detect-effect-table
 * @tags testing
 */

import codeql.ucode.m3.Models

from BuiltinSystemCall c
where
  c.getLocation().getFile().getBaseName() = "luci" and
  c.getParent*() = rpcCallFn("setBlockDetect") and
  stringLiteralValue(c.getArgument(0).(UCODE::String)) =
    "/sbin/block detect > /etc/config/fstab" and
  not exists(c.getArgument(1))
select "callback_body_call" as observation_kind,
  "setBlockDetect" as method,
  "system" as sink_kind,
  "/sbin/block detect > /etc/config/fstab" as command,
  c.getLocation().getFile().getRelativePath() as source_path,
  c.getLocation().getStartLine() as start_line,
  c.getLocation().getStartColumn() as start_column,
  c.getLocation().getEndLine() as end_line,
  c.getLocation().getEndColumn() as end_column
