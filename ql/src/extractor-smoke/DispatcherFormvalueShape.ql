/**
 * @name Direct http.formvalue source shape
 * @description Test-only syntactic observation; receiver binding and runtime behavior are not resolved.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/testing/dispatcher-formvalue-shape
 * @tags testing
 */
import codeql.ucode.ast.internal.TreeSitter
import codeql.files.FileSystem

from UCODE::CallExpression call, UCODE::MemberExpression member, string arg0, string arg1, int arity
where
  member = call.getFunction() and
  member.getObject().(UCODE::Identifier).getValue() = "http" and
  member.getProperty().getValue() = "formvalue" and
  not exists(member.getOptionalChain()) and
  not exists(call.getOptionalChain()) and
  (arg0 = call.getArguments().getChild(0).getAPrimaryQlClass() or
   arg0 = "none" and not exists(call.getArguments().getChild(0))) and
  (arg1 = call.getArguments().getChild(1).getAPrimaryQlClass() or
   arg1 = "none" and not exists(call.getArguments().getChild(1))) and
  arity = count(int i | exists(call.getArguments().getChild(i)))
select call, "direct formvalue at " + call.getLocation().getFile().getBaseName() + ":" +
  call.getLocation().getStartLine().toString() + ":" + arg0 + ":" + arg1 + ":" + arity.toString()
