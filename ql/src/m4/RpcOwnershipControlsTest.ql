/**
 * @name RPC ownership fixture eligibility
 * @description Test-only inventory, independent of the ownership/taint guard.
 * @kind table
 * @id ucode/test/rpc-ownership-controls
 */
import codeql.ucode.m3.Models

from UCODE::AstNode node, string role, string method
where
  method = rpcMethodName(node) and
  (
    node instanceof RequestArgsAccess and role = "request-args"
    or
    node instanceof NamedFsPopenCall and role = "fs-popen"
  )
select node, role, method
