/**
 * @name luci.sys conntrack_list and process_list fixed popen
 * @description M4: named fs popen inside luci.sys conntrack_list and process_list. getConntrackList/getProcessList.call are thin wrappers with no request.args. Not interprocedural path_found from luci.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/luci-sys-status-exec
 * @tags testing
 */

import codeql.ucode.m3.Models

predicate conntrackFallbackLiteral(NamedFsPopenCall c) {
  exists(UCODE::String s |
    s = c.getArgument(0) and
    stringLiteralValue(s).regexpMatch(".*/usr/sbin/conntrack.*")
  )
}

predicate busyboxTopLiteral(NamedFsPopenCall c) {
  exists(UCODE::String s |
    s = c.getArgument(0) and
    stringLiteralValue(s).regexpMatch(".*/bin/busybox top.*")
  )
}

from NamedFsPopenCall c, string helper, string rpc
where
  inProcessList(c) and busyboxTopLiteral(c) and helper = "process_list" and rpc = "getProcessList"
  or
  inConntrackList(c) and conntrackFallbackLiteral(c) and helper = "conntrack_list" and
  rpc = "getConntrackList"
select c,
  rpc + " via " + helper + " popen at line " + c.getLocation().getStartLine().toString(), c, "popen"
