/**
 * @name UCI commit helper observation
 * @description Test-only conservative same-file helper association and positional formal forwarding; no runtime or security claim.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/testing/uci-helper-observation
 * @tags testing
 */
import codeql.ucode.m3.Models
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter

private predicate forwards(UCODE::FunctionDeclaration f, UCODE::CallExpression call, int i) {
  exists(UCODE::Identifier formal, UCODE::Identifier arg, VariableReadAccess read |
    formal = f.getParameters().getChild(i) and
    arg = call.getArguments().getChild(i) and
    read.getAstNode() = TIdentifier(arg) and
    read.getVariable().getAstNode() = TIdentifier(formal)
  )
}

from NamedCall site, UCODE::FunctionDeclaration helper, UCODE::CallExpression forward,
  UCODE::MemberExpression member
where
  site.getName() = "ubus_call" and sameFileCall(site, helper) and
  stringLiteralValue(site.getArgument(0).(UCODE::String)) = "uci" and
  stringLiteralValue(site.getArgument(1).(UCODE::String)) = "commit" and
  exists(site.getArgument(2)) and not exists(site.getArgument(3)) and
  forward.getParent*() = helper.getBody() and
  not exists(UCODE::AstNode nested |
    nested = forward.getParent+() and nested.getParent*() = helper.getBody() and
    (nested instanceof UCODE::FunctionDeclaration or nested instanceof UCODE::FunctionExpression or
      nested instanceof UCODE::ArrowFunction)
  ) and
  member = forward.getFunction() and
  member.getObject().(UCODE::Identifier).getValue() = "ubus" and
  member.getProperty().(UCODE::PropertyIdentifier).getValue() = "call" and
  not exists(member.getOptionalChain()) and not exists(forward.getOptionalChain()) and
  forwards(helper, forward, 0) and forwards(helper, forward, 1) and forwards(helper, forward, 2) and
  not exists(forward.getArguments().getChild(3)) and not exists(helper.getParameters().getChild(3))
select site, "UCI commit helper observation: " + helper.getLocation().getStartLine().toString() +
  ":" + forward.getLocation().getStartLine().toString(), forward, "forwarding call"
