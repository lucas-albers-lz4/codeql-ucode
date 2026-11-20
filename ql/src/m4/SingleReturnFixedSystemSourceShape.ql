/**
 * @name One-return fixed system callback source shape
 * @description Bounded lexical observation; no runtime, ingress, authorization or general guard-absence claim.
 * @id ucode/testing/single-return-fixed-system-source-shape
 * @tags testing
 */

import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.Diagnostics
import codeql.ucode.m3.Models

/** All direct keys must be identifier keys and unique, including call keys. */
predicate plainUnique(UCODE::Object obj) {
  not exists(UCODE::AstNode child |
    child = obj.getChild(_) and
    not exists(UCODE::Pair pair |
      pair = child and exists(pair.getKey().(UCODE::PropertyIdentifier))
    )
  ) and
  not exists(UCODE::Pair a, UCODE::Pair b |
    a = obj.getChild(_) and
    b = obj.getChild(_) and
    a != b and
    a.getKey().(UCODE::PropertyIdentifier).getValue() =
      b.getKey().(UCODE::PropertyIdentifier).getValue()
  )
}

predicate validEntry(UCODE::AstNode node) {
  exists(UCODE::Pair pair, UCODE::Object body, UCODE::Pair call |
    pair = node and
    exists(pair.getKey().(UCODE::PropertyIdentifier)) and
    body = pair.getValue() and
    plainUnique(body) and
    call = body.getChild(_) and
    call.getKey().(UCODE::PropertyIdentifier).getValue() = "call" and
    exists(call.getValue().(UCODE::FunctionExpression))
  )
}


/** Only this complete source shape is observed. Every nonmatch is unassessed. */
predicate oneReturnShape(UCODE::FunctionExpression fn, BuiltinSystemCall c) {
  not exists(fn.getName()) and
  exists(UCODE::ReturnStatement ret, UCODE::Object obj,
      UCODE::Pair pair, UCODE::BinaryExpression comparison, UCODE::String literal |
    ret = fn.getBody().getChild(_) and
    not exists(UCODE::AstNode other |
      other = fn.getBody().getChild(_) and other != ret
    ) and
    obj = ret.getChild() and
    pair = obj.getChild(_) and
    pair.getKey().(UCODE::PropertyIdentifier).getValue() = "result" and
    not exists(UCODE::AstNode other |
      other = obj.getChild(_) and other != pair
    ) and
    comparison = pair.getValue() and
    comparison.getLeft() = c and
    comparison.getOperator() = "==" and
    comparison.getRight().(UCODE::Number).getValue() = "0" and
    not exists(c.getOptionalChain()) and
    literal = c.getArgument(0) and
    not exists(c.getArgument(1)) and
    exists(literal.getChild(_).(UCODE::StringFragment)) and
    not exists(UCODE::AstNode child |
      child = literal.getChild(_) and not child instanceof UCODE::StringFragment
    )
  )
}

from
  UCODE::Program program, UCODE::LexicalDeclaration declaration, UCODE::VariableDeclarator binding,
  UCODE::Object methods, UCODE::ReturnStatement ret, UCODE::Object returned, UCODE::Pair rp,
  UCODE::Pair entry, UCODE::Object body, UCODE::Pair call, UCODE::FunctionExpression fn, BuiltinSystemCall c
where
  program.getLocation().getFile().getRelativePath().matches("modules/%/root/usr/share/rpcd/ucode/luci") and
  not exists(ExtractionError error |
    error.getLocation().getFile() = program.getLocation().getFile()
  ) and
  declaration = program.getChild(_) and
  declaration.getKind().(UCODE::Token).getValue() = "const" and
  binding = declaration.getChild(_) and
  binding.getName().getValue() = "methods" and
  methods = binding.getValue() and
  ret = program.getChild(_) and
  returned = ret.getChild() and
  plainUnique(returned) and
  not exists(UCODE::ReturnStatement other | other = program.getChild(_) and other != ret) and
  rp = returned.getChild(_) and
  rp.getKey().(UCODE::PropertyIdentifier).getValue() = "luci" and
  rp.getValue().(UCODE::Identifier).getValue() = "methods" and
  not exists(UCODE::Identifier id |
    id.getLocation().getFile() = program.getLocation().getFile() and
    id.getValue() = "methods" and
    id != binding.getName() and
    id != rp.getValue()
  ) and
  not exists(UCODE::ShorthandPropertyIdentifier shorthand |
    shorthand.getLocation().getFile() = program.getLocation().getFile() and
    shorthand.getValue() = "methods"
  ) and
  entry = methods.getChild(_) and
  body = entry.getValue() and
  plainUnique(methods) and
  not exists(UCODE::AstNode child | child = methods.getChild(_) and not validEntry(child)) and
  call = body.getChild(_) and
  call.getKey().(UCODE::PropertyIdentifier).getValue() = "call" and
  fn = call.getValue()
  and entry.getKey().(UCODE::PropertyIdentifier).getValue() = "setBlockDetect"
  and c.getParent*() = fn
  and exists(c.getArgument(0).(UCODE::String))
  and oneReturnShape(fn, c)
select c.getLocation().getFile().getRelativePath() as source_path,
  c.getLocation().getStartLine() as start_line,
  c.getLocation().getStartColumn() as start_column,
  c.getLocation().getEndLine() as end_line,
  c.getLocation().getEndColumn() as end_column,
  stringLiteralValue(c.getArgument(0).(UCODE::String)) as command
