/** @name Testing-only namespace stat model
 * @description Exact source-attributed namespace stat call and argument.
 * @kind table
 * @id ucode/testing/issue155-namespace-stat-model
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models

from SourceDeclaredFsNamespaceStatCall call
select call.getLocation().getFile().getBaseName() as path, call as call_node,
  call.getFunction() as callee_node, call.getPathArgument() as argument_node
