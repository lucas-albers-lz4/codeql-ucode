/**
 * @name LuCI backend source-declared callbacks
 * @description Bounded source shape, not runtime registration or reachability.
 * @id ucode/m4/luci-backend-declarations
 * @tags testing
 */

import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.Diagnostics

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

from
  UCODE::Program program, UCODE::LexicalDeclaration declaration, UCODE::VariableDeclarator binding,
  UCODE::Object methods, UCODE::ReturnStatement ret, UCODE::Object returned, UCODE::Pair rp,
  UCODE::Pair entry, UCODE::Object body, UCODE::Pair call, UCODE::FunctionExpression fn
where
  program.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
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
select "source_declared_callback" as observation_kind, "luci" as ubus_object,
  entry.getKey().(UCODE::PropertyIdentifier).getValue() as method,
  program.getLocation().getFile().getRelativePath() as source_path,
  fn.getLocation().getStartLine() as start_line, fn.getLocation().getStartColumn() as start_column,
  fn.getLocation().getEndLine() as end_line, fn.getLocation().getEndColumn() as end_column
