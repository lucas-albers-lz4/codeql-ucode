/**
 * @name luci request.args to popen/system
 * @description M4: syntactic local taint from request.args into named fs popen or builtin system, labeled by rpcd method.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/request-args-exec
 * @tags testing
 */

import codeql.ucode.m3.Models

string quoteNote(RequestArgsAccess src) {
  if wrappedByShellquote(src) then result = " via shellquote" else result = ""
}

/** The legacy luci basename and the explicitly staged application identities. */
predicate eligibleSource(RequestArgsAccess src) {
  src.getLocation().getFile().getBaseName() = "luci"
  or
  src.getLocation().getFile().getRelativePath() =
    ["usr/share/rpcd/ucode/docker_rpc.uc", "usr/share/rpcd/ucode/ddns.uc",
     "usr/share/rpcd/ucode/tailscale.uc", "usr/share/rpcd/ucode/example.uc",
     "usr/share/rpcd/ucode/rustdesk-server.uc", "usr/share/rpcd/ucode/wifihistory.uc",
     "usr/share/rpcd/ucode/weechat.uc"]
}

from RequestArgsAccess src, NamedCall sink, string method
where
  eligibleSource(src) and
  src.getProperty().getValue() != "args" and
  method = rpcMethodName(sink) and
  (sink instanceof NamedFsPopenCall or sink instanceof BuiltinSystemCall) and
  taintReachesSink(src, sink)
select src, method + " request.args reaches " + sink.getName() + quoteNote(src), sink, sink.getName()
