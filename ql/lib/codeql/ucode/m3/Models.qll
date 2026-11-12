/**
 * Bounded M3 models over generated TreeSitter nodes.
 * Same-file calls, named `popen` from `'fs'`, builtin `system()`,
 * and syntactic local taint for the synthetic fixtures.
 */

import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter

/** Gets the text of a string literal (joined fragments). */
string stringLiteralValue(UCODE::String s) {
  result = strictconcat(int i, UCODE::StringFragment frag |
      frag = s.getChild(i)
    |
      frag.getValue() order by i
    )
}

/** An `import { name } from 'module'` specifier. */
predicate namedImport(UCODE::ImportStatement imp, string moduleName, string localName) {
  moduleName = stringLiteralValue(imp.getSource()) and
  exists(UCODE::ImportSpecifier spec |
    spec = imp.getClause().getNamed().getChild(_) and
    localName = spec.getName().(UCODE::Identifier).getValue() and
    not exists(spec.getAlias())
  )
}

/** Callee identifier of a call, including when the function field is a wrapper expression. */
UCODE::Identifier calleeIdent(UCODE::CallExpression c) {
  result = c.getFunction()
  or
  result = c.getFunction().getAFieldOrChild()
}

/** A call whose callee is the identifier `name`. */
class NamedCall extends UCODE::CallExpression {
  string name;

  NamedCall() { name = calleeIdent(this).getValue() }

  string getName() { result = name }

  UCODE::AstNode getArgument(int i) { result = this.getArguments().getChild(i) }
}

/** `popen(...)` where `popen` is imported from `'fs'` in the same file. */
class NamedFsPopenCall extends NamedCall {
  NamedFsPopenCall() {
    this.getName() = "popen" and
    exists(UCODE::ImportStatement imp |
      imp.getLocation().getFile() = this.getLocation().getFile() and
      namedImport(imp, "fs", "popen")
    )
  }
}

/** Global builtin `system(...)` (stdlib, not an fs export). */
class BuiltinSystemCall extends NamedCall {
  BuiltinSystemCall() {
    this.getName() = "system" and
    not namedImport(any(UCODE::ImportStatement imp |
        imp.getLocation().getFile() = this.getLocation().getFile()
      ), _, "system")
  }
}

/** Same-file `function name(...) { ... }`. */
UCODE::FunctionDeclaration functionDecl(string name) {
  result.getName().getValue() = name
}

/** A call to a same-file function declaration. */
predicate sameFileCall(NamedCall c, UCODE::FunctionDeclaration def) {
  def = functionDecl(c.getName()) and
  c.getLocation().getFile() = def.getLocation().getFile()
}

/** `callPackageVersionCheck('netifd')` (literal package name). */
class CallPackageVersionCheckNetifd extends NamedCall {
  CallPackageVersionCheckNetifd() {
    this.getName() = "callPackageVersionCheck" and
    stringLiteralValue(this.getArgument(0).(UCODE::String)) = "netifd"
  }
}

/** Property identifier token value. */
string propertyName(UCODE::AstNode n) {
  result = n.(UCODE::PropertyIdentifier).getValue()
  or
  result = n.(UCODE::Identifier).getValue()
}

/** `getFeatures: { call: function(...) { ... } }`. */
UCODE::FunctionExpression getFeaturesCallFn() {
  exists(UCODE::Pair method, UCODE::Pair callPair, UCODE::Object body |
    propertyName(method.getKey()) = "getFeatures" and
    body = method.getValue() and
    callPair = body.getChild(_) and
    propertyName(callPair.getKey()) = "call" and
    result = callPair.getValue()
  )
}

/** Holds if `n` is inside the `getFeatures.call` function. */
predicate inGetFeaturesCall(UCODE::AstNode n) { n.getParent*() = getFeaturesCallFn() }

/** `request.args` or `request.args.<k>`. */
class RequestArgsAccess extends UCODE::MemberExpression {
  RequestArgsAccess() {
    exists(UCODE::MemberExpression inner |
      this.getObject() = inner and
      inner.getObject().(UCODE::Identifier).getValue() = "request" and
      inner.getProperty().getValue() = "args"
    )
    or
    this.getObject().(UCODE::Identifier).getValue() = "request" and
    this.getProperty().getValue() = "args"
  }
}

/** Syntactic local taint: node is a request.args access or a tree containing one. */
predicate locallyTainted(UCODE::AstNode n) {
  n instanceof RequestArgsAccess
  or
  locallyTainted(n.getAFieldOrChild())
}

/** Positive control: a sink argument is locally tainted. */
predicate taintReachesSink(UCODE::AstNode source, NamedCall sink) {
  source instanceof RequestArgsAccess and
  locallyTainted(sink.getArgument(_)) and
  source.getParent*() = sink.getArgument(_)
}
