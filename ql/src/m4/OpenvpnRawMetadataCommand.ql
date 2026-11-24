/**
 * @name Unquoted OpenVPN metadata in a shell command
 * @description A generateKey RPC argument is interpolated directly into a command assigned to cmd and then passed to fs.popen. This reports only the raw source form; absence is not a sanitization verdict.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/openvpn-raw-metadata-command
 * @tags testing
 */

import codeql.ucode.m3.Models

/** The RPC formal, identified by its declaration rather than its spelling. */
private UCODE::Identifier generateKeyRequest(UCODE::FunctionExpression fn) {
  fn = rpcCallFn("generateKey") and
  result = fn.getParameters().getChild(_)
}

/** The exact request argument access in the generated command. */
private UCODE::MemberExpression metadata(UCODE::Identifier formal, UCODE::FunctionExpression fn) {
  exists(UCODE::MemberExpression args |
    result.getObject() = args and
    args.getObject().(UCODE::Identifier).getValue() = formal.getValue() and
    args.getProperty().getValue() = "args" and
    result.getProperty().getValue() = "cl_meta" and
    result.getParent*() = fn
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
    formal = generateKeyRequest(fn) and source = metadata(formal, fn) and
    source.getLocation().getFile().getRelativePath() =
      "usr/share/rpcd/ucode/luci.openvpn.uc" and
    sub.getChild() = source and sub = template.getChild(_) and
    assignment.getRight() = template and
    command = assignment.getLeft() and command.getValue() = "cmd" and
    sink.getArgument(0).(UCODE::Identifier).getValue() = command.getValue() and
    assignment.getParent*() = fn and sink.getParent*() = fn and
    assignment.getParent*() = branch.getConsequence() and
    branch.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(UCODE::AssignmentExpression write |
      write != assignment and write.getLeft().(UCODE::Identifier).getValue() = command.getValue() and
      write.getParent*() = fn and
      write.getLocation().getStartLine() > assignment.getLocation().getStartLine() and
      write.getLocation().getStartLine() < sink.getLocation().getStartLine() and
      not write.getParent*() = branch.getAlternative()
    )
  )
}

from UCODE::MemberExpression source, UCODE::AssignmentExpression assignment,
  NamedFsPopenCall sink
where rawMetadataCommand(source, assignment, sink)
select source,
  "RPC metadata is interpolated directly into a command passed to fs.popen.",
  sink, "popen", assignment.getLocation().getStartLine(),
  source.getLocation().getStartLine(), source.getLocation().getStartColumn(),
  source.getLocation().getEndLine(), source.getLocation().getEndColumn(),
  sink.getLocation().getStartLine(), sink.getLocation().getStartColumn(),
  sink.getLocation().getEndLine(), sink.getLocation().getEndColumn()
