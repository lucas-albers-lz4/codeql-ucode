/** Test-only inventory of modeled sources and sinks, independent of query path eligibility. */
import codeql.ucode.m3.Models

from UCODE::AstNode node, string role, string method
where
  method = rpcMethodName(node) and
  (
    node instanceof RequestArgsAccess and role = "request-args"
    or
    node instanceof BuiltinSystemCall and role = "system"
  )
select node, role, method
