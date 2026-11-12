/**
 * @name luci.sys conntrack_list and process_list fixed popen
 * @description M4: fixed named fs popen in luci.sys, paired with indexed RPC wrappers. This is a syntactic inventory, not interprocedural path_found from luci.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/luci-sys-status-exec
 * @tags testing
 */

import codeql.ucode.m3.Models

/** The indexed luci wrapper calls the named helper imported from luci.sys. */
predicate dispatch(string rpc, string helper) {
  exists(UCODE::FunctionExpression fn, NamedCall call, UCODE::ImportStatement imp,
    UCODE::VariableDeclarator methods, UCODE::Object methodObject, UCODE::Object body,
    UCODE::Pair method, UCODE::Pair callPair |
    methods.getName().getValue() = "methods" and methodObject = methods.getValue() and
    method = methodObject.getChild(_) and propertyName(method.getKey()) = rpc and
    body = method.getValue() and callPair = body.getChild(_) and
    propertyName(callPair.getKey()) = "call" and fn = callPair.getValue() and
    fn.getLocation().getFile() = methods.getLocation().getFile() and
    fn.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
    call.getParent*() = fn and call.getName() = helper and
    imp.getLocation().getFile() = fn.getLocation().getFile() and
    namedImport(imp, "luci.sys", helper)
  )
}

/** The exact fixture idiom: open procfs, then assign popen only under if (!nfct). */
predicate conntrackFallback(NamedFsPopenCall c) {
  exists(UCODE::VariableDeclarator decl, NamedCall openCall, UCODE::ImportStatement imp, UCODE::IfStatement branch,
    UCODE::UnaryExpression condition, UCODE::AssignmentExpression assign, string name |
    decl.getParent*() = conntrackListFn() and
    name = decl.getName().getValue() and openCall = decl.getValue() and
    openCall.getName() = "open" and
    imp.getLocation().getFile() = openCall.getLocation().getFile() and
    namedImport(imp, "fs", "open") and
    stringLiteralValue(openCall.getArgument(0).(UCODE::String)) = "/proc/net/nf_conntrack" and
    branch.getParent*() = conntrackListFn() and
    condition = branch.getCondition().getAFieldOrChild() and
    condition.getOperator() = "!" and condition.getArgument().(UCODE::Identifier).getValue() = name and
    assign.getParent*() = branch.getConsequence() and
    assign.getLeft().(UCODE::Identifier).getValue() = name and assign.getRight() = c and
    decl.getLocation().getStartLine() < branch.getLocation().getStartLine()
  )
}

from NamedFsPopenCall c, string helper, string rpc, string command
where
  (
    inProcessList(c) and helper = "process_list" and rpc = "getProcessList" and
    command = "/bin/busybox top -bn1"
    or
    inConntrackList(c) and conntrackFallback(c) and helper = "conntrack_list" and
    rpc = "getConntrackList" and command = "/usr/sbin/conntrack -L -o extended"
  ) and
  stringLiteralValue(c.getArgument(0).(UCODE::String)) = command and dispatch(rpc, helper)
select c,
  rpc + " via " + helper + " popen " + command + " at line " + c.getLocation().getStartLine().toString(), c, "popen"
