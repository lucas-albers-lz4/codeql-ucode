/**
 * @name Unquoted OpenVPN metadata in a shell command
 * @description A generateKey RPC argument is directly interpolated into a command assigned to cmd and later supplied to fs.popen, under conservative same-body binding guards. Absence is not a sanitization verdict.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/openvpn-raw-metadata-command
 * @tags testing
 */

import codeql.ucode.m3.Models

/** The selected RPC formal. Uses below are matched conservatively by spelling. */
private UCODE::Identifier generateKeyRequest(UCODE::FunctionExpression fn) {
  fn = rpcCallFn("generateKey") and
  result = fn.getParameters().getChild(_)
}

/** Exclude nested callable bodies: same-name uses there are not tied to this RPC invocation. */
private predicate inDirectRpcBody(UCODE::AstNode n, UCODE::FunctionExpression fn) {
  n.getParent*() = fn and
  not exists(UCODE::FunctionExpression nested |
    nested != fn and n.getParent*() = nested
  ) and
  not exists(UCODE::FunctionDeclaration nested | n.getParent*() = nested) and
  not exists(UCODE::ArrowFunction nested | n.getParent*() = nested)
}

/** Reject known local shadows and writes to the request formal. This is not SSA. */
private predicate stableRequestFormal(UCODE::Identifier formal, UCODE::FunctionExpression fn) {
  not exists(UCODE::VariableDeclarator d |
    d.getName().getValue() = formal.getValue() and d.getParent*() = fn
  ) and
  not exists(UCODE::AssignmentExpression a |
    a.getLeft().(UCODE::Identifier).getValue() = formal.getValue() and a.getParent*() = fn
  ) and
  not exists(UCODE::AugmentedAssignmentExpression a |
    a.getLeft().(UCODE::Identifier).getValue() = formal.getValue() and a.getParent*() = fn
  ) and
  not exists(UCODE::CatchClause c |
    c.getParameter().getValue() = formal.getValue() and c.getParent*() = fn
  )
}

/** One uninitialized local `cmd`; a second same-name declaration makes uses ambiguous. */
private predicate singleCommandLocal(UCODE::Identifier command, UCODE::FunctionExpression fn) {
  exists(UCODE::VariableDeclarator d |
    d.getName().getValue() = command.getValue() and
    inDirectRpcBody(d, fn) and not exists(d.getValue()) and
    not exists(UCODE::VariableDeclarator other |
      other != d and other.getName().getValue() = command.getValue() and
      other.getParent*() = fn
    )
  )
}

/** The exact request argument access in the generated command. */
private UCODE::MemberExpression metadata(UCODE::Identifier formal, UCODE::FunctionExpression fn) {
  exists(UCODE::MemberExpression args |
    result.getObject() = args and
    args.getObject().(UCODE::Identifier).getValue() = formal.getValue() and
    args.getProperty().getValue() = "args" and
    result.getProperty().getValue() = "cl_meta" and
    inDirectRpcBody(result, fn)
  )
}

/** A raw substitution in the value assigned to cmd, with a direct fs.popen(cmd). */
private predicate rawMetadataCommand(
  UCODE::MemberExpression source, UCODE::AssignmentExpression assignment,
  NamedFsPopenCall sink
) {
  exists(
    UCODE::Identifier formal, UCODE::FunctionExpression fn, UCODE::IfStatement branch,
    UCODE::TemplateSubstitution sub,
    UCODE::TemplateString template, UCODE::Identifier command
  |
    formal = generateKeyRequest(fn) and stableRequestFormal(formal, fn) and
    source = metadata(formal, fn) and
    source.getLocation().getFile().getRelativePath() =
      "usr/share/rpcd/ucode/luci.openvpn.uc" and
    sub.getChild() = source and sub = template.getChild(_) and
    assignment.getRight() = template and
    command = assignment.getLeft() and command.getValue() = "cmd" and
    singleCommandLocal(command, fn) and
    sink.getArgument(0).(UCODE::Identifier).getValue() = command.getValue() and
    inDirectRpcBody(assignment, fn) and inDirectRpcBody(sink, fn) and
    assignment.getParent*() = branch.getConsequence() and
    branch.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(UCODE::AssignmentExpression write |
      write != assignment and write.getLeft().(UCODE::Identifier).getValue() = command.getValue() and
      write.getParent*() = fn and
      write.getLocation().getStartLine() > assignment.getLocation().getStartLine() and
      write.getLocation().getStartLine() < sink.getLocation().getStartLine() and
      not write.getParent*() = branch.getAlternative()
    ) and
    not exists(UCODE::AugmentedAssignmentExpression write |
      write.getLeft().(UCODE::Identifier).getValue() = command.getValue() and
      write.getParent*() = fn and
      write.getLocation().getStartLine() > assignment.getLocation().getStartLine() and
      write.getLocation().getStartLine() < sink.getLocation().getStartLine()
    )
  )
}

from UCODE::MemberExpression source, UCODE::AssignmentExpression assignment,
  NamedFsPopenCall sink
where rawMetadataCommand(source, assignment, sink)
select source,
  "RPC metadata is directly interpolated into a command later passed to fs.popen at line " +
    sink.getLocation().getStartLine().toString() + "; review the command path."
