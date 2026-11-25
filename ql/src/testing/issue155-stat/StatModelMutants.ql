/** @name Testing-only stat argument guard mutations
 * @description Exercises unary arity and spread exclusion; no runtime assertion.
 * @kind table
 * @id ucode/testing/issue155-stat-argument-mutants
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, UCODE::AstNode arg, string mutation
where sourceDeclaredFsCall(call, "stat") and arg = call.getArguments().getChild(0) and
  (
    mutation = "arity" and arg instanceof UCODE::Expression
    or
    mutation = "spread" and not exists(int i | i != 0 and exists(call.getArguments().getChild(i)))
  )
select mutation, call.getLocation().getFile().getRelativePath() as path,
  call as call_node, call.getFunction() as callee_node, arg as argument_node
