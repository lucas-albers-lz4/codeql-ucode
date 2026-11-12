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

predicate sysfixtimeLiteral(BuiltinSystemCall c) {
  exists(UCODE::String s |
    s = c.getArgument(0) and
    stringLiteralValue(s).regexpMatch(".*sysfixtime.*")
  )
}

from NamedCall c, string method, string kind
where
  c.getLocation().getFile().getBaseName() = "luci" and
  (
    inRpcCall(c, "getBlockDevices") and
    c instanceof NamedFsPopenCall and
    method = "getBlockDevices" and
    kind = "popen"
    or
    inRpcCall(c, "setBlockDetect") and
    c instanceof BuiltinSystemCall and
    method = "setBlockDetect" and
    kind = "system"
    or
    inRpcCall(c, "setLocaltime") and
    c instanceof BuiltinSystemCall and
    sysfixtimeLiteral(c) and
    method = "setLocaltime" and
    kind = "system"
  )
select c, method + " " + kind + " at line " + c.getLocation().getStartLine().toString(), c, kind
