/**
 * @name luci getBlockDevices/setBlockDetect/sysfixtime exec
 * @description M4: fixed named fs popen and builtin system inside getBlockDevices.call, setBlockDetect.call, and setLocaltime.call sysfixtime. Not request.args taint. Not path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/block-device-exec
 * @tags testing
 */

import codeql.ucode.m3.Models

predicate inRpcCall(UCODE::AstNode n, string name) { n.getParent*() = rpcCallFn(name) }

from NamedCall c, string method, string kind, string command
where
  c.getLocation().getFile().getBaseName() = "luci" and
  command = stringLiteralValue(c.getArgument(0).(UCODE::String)) and
  (
    inRpcCall(c, "getBlockDevices") and
    c instanceof NamedFsPopenCall and
    method = "getBlockDevices" and
    kind = "popen" and
    command = "/sbin/block info 2>/dev/null"
    or
    inRpcCall(c, "setBlockDetect") and
    c instanceof BuiltinSystemCall and
    method = "setBlockDetect" and
    kind = "system" and
    command = "/sbin/block detect > /etc/config/fstab"
    or
    inRpcCall(c, "setLocaltime") and
    c instanceof BuiltinSystemCall and
    method = "setLocaltime" and
    kind = "system" and
    command = "/etc/init.d/sysfixtime restart >/dev/null"
  )
select c, method + " " + kind + " at line " + c.getLocation().getStartLine().toString(), c, method,
  kind, command
