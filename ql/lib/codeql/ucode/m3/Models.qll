/**
 * Bounded M3/M4 models over generated TreeSitter nodes.
 * Same-file calls, named `popen` from `'fs'`, builtin `system()`,
 * syntactic local taint, and enclosing rpcd method names.
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

/** `name: { call: function(...) { ... } }` method body. */
UCODE::FunctionExpression rpcCallFn(string name) {
  exists(UCODE::Pair method, UCODE::Pair callPair, UCODE::Object body |
    name = propertyName(method.getKey()) and
    body = method.getValue() and
    callPair = body.getChild(_) and
    propertyName(callPair.getKey()) = "call" and
    result = callPair.getValue()
  )
}

/** `getFeatures: { call: function(...) { ... } }`. */
UCODE::FunctionExpression getFeaturesCallFn() { result = rpcCallFn("getFeatures") }

/** Holds if `n` is inside the `getFeatures.call` function. */
predicate inGetFeaturesCall(UCODE::AstNode n) { n.getParent*() = getFeaturesCallFn() }

/** Enclosing rpcd method name for a node inside `methods.<name>.call`. */
string rpcMethodName(UCODE::AstNode n) {
  exists(string name, UCODE::FunctionExpression fn |
    fn = rpcCallFn(name) and
    n.getParent*() = fn and
    result = name
  )
}

/** `shellquote(...)` wrapping `n` (complete-argument quoting, not a global sanitizer). */
predicate wrappedByShellquote(UCODE::AstNode n) {
  exists(NamedCall sq |
    sq.getName() = "shellquote" and
    n.getParent*() = sq.getArgument(0)
  )
}

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

/** Two nodes sit in the same rpcd `methods.<name>.call` body (one function node). */
predicate sameRpcMethod(UCODE::AstNode a, UCODE::AstNode b) {
  exists(UCODE::FunctionExpression fn | fn = rpcCallFn(_) and a.getParent*() = fn and b.getParent*() = fn)
}

/**
 * Same-function name binding from a tainted initializer or assignment.
 * Not CFG/SSA: later reassignment in the same method is not distinguished.
 */
predicate taintedBinding(RequestArgsAccess source, string name) {
  exists(UCODE::VariableDeclarator d |
    source.getParent*() = d.getValue() and
    name = d.getName().getValue() and
    sameRpcMethod(source, d)
  )
  or
  exists(UCODE::AssignmentExpression a |
    source.getParent*() = a.getRight() and
    name = a.getLeft().(UCODE::Identifier).getValue() and
    sameRpcMethod(source, a)
  )
  or
  exists(UCODE::VariableDeclarator d, UCODE::Identifier inner |
    inner.getParent*() = d.getValue() and
    taintedBinding(source, inner.getValue()) and
    name = d.getName().getValue() and
    sameRpcMethod(source, d)
  )
  or
  exists(UCODE::AssignmentExpression a, UCODE::Identifier inner |
    inner.getParent*() = a.getRight() and
    taintedBinding(source, inner.getValue()) and
    name = a.getLeft().(UCODE::Identifier).getValue() and
    sameRpcMethod(source, a)
  )
}

/** Positive control: a sink argument is locally tainted, including same-function bindings. */
predicate taintReachesSink(UCODE::AstNode source, NamedCall sink) {
  source instanceof RequestArgsAccess and
  exists(UCODE::AstNode arg | arg = sink.getArgument(_) |
    source.getParent*() = arg
    or
    exists(UCODE::Identifier use |
      use.getParent*() = arg and
      sameRpcMethod(source, use) and
      taintedBinding(source, use.getValue())
    )
  )
}

/** Direct child index of `child` in template `tmpl`. */
int templateChildIndex(UCODE::TemplateString tmpl, UCODE::AstNode child) { child = tmpl.getChild(result) }

/**
 * Documented unsupported template contexts: leading substitution (executable
 * selection), `sh -c` program text, or double-quote embedding.
 */
predicate unsupportedShellquoteTemplate(UCODE::TemplateString tmpl, int subIdx) {
  tmpl.getChild(subIdx) instanceof UCODE::TemplateSubstitution and
  (
    subIdx = 0
    or
    exists(int j, UCODE::StringFragment prefix |
      prefix = tmpl.getChild(j) and j < subIdx and
      prefix.getValue().regexpMatch("(?i).*\\bsh\\s+-c\\s*$")
    )
    or
    exists(UCODE::StringFragment frag |
      frag = tmpl.getChild(_) and frag.getValue().regexpMatch(".*[\"\\\\].*")
    )
  )
}

/**
 * Tainted `shellquote` is a non-leading template substitution with literal text
 * before and after — a complete shell word beside a fixed command, not
 * executable selection or interpreter/dquote embedding.
 */
predicate completeQuotedTemplateArg(RequestArgsAccess src, NamedCall sink) {
  taintReachesSink(src, sink) and
  exists(
    NamedCall sq, UCODE::TemplateSubstitution sub, UCODE::TemplateString tmpl, int subIdx
  |
    sq.getName() = "shellquote" and
    src.getParent*() = sq.getArgument(0) and
    sq.getParent*() = sub and
    sub = tmpl.getChild(subIdx) and
    tmpl = sink.getArgument(_) and
    exists(int j, UCODE::StringFragment prefix |
      prefix = tmpl.getChild(j) and j < subIdx and prefix.getValue().regexpMatch(".*\\S.*")
    ) and
    exists(int k, UCODE::StringFragment suffix |
      suffix = tmpl.getChild(k) and k > subIdx and suffix.getValue().regexpMatch(".*\\S.*")
    ) and
    not unsupportedShellquoteTemplate(tmpl, subIdx)
  )
}

/** The whole sink argument is `shellquote(tainted)` — executable/command selection. */
predicate quotedEntireCommand(RequestArgsAccess src, NamedCall sink) {
  taintReachesSink(src, sink) and
  exists(NamedCall sq |
    sq.getName() = "shellquote" and
    src.getParent*() = sq.getArgument(0) and
    sq = sink.getArgument(_)
  )
}

/** Shell-injection candidate: taint reaches the sink and is not a complete quoted argument. */
predicate shellInjectionCandidate(RequestArgsAccess src, NamedCall sink) {
  taintReachesSink(src, sink) and
  not completeQuotedTemplateArg(src, sink)
}

/** `export function init_action` in installed luci.sys (`sys.uc`). */
UCODE::FunctionDeclaration initActionFn() {
  result = functionDecl("init_action") and
  result.getLocation().getFile().getBaseName() = "sys.uc"
}

/** Holds if `n` is inside `init_action` in `sys.uc`. */
predicate inInitAction(UCODE::AstNode n) { n.getParent*() = initActionFn() }

/** `setInitAction: { call: function(...) { ... } }`. */
UCODE::FunctionExpression setInitActionCallFn() {
  exists(UCODE::Pair method, UCODE::Pair callPair, UCODE::Object body |
    propertyName(method.getKey()) = "setInitAction" and
    body = method.getValue() and
    callPair = body.getChild(_) and
    propertyName(callPair.getKey()) = "call" and
    result = callPair.getValue()
  )
}

/** Holds if `n` is inside the `setInitAction.call` function. */
predicate inSetInitActionCall(UCODE::AstNode n) { n.getParent*() = setInitActionCallFn() }
