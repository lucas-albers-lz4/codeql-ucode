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

/** Holds if an import binds `localName` in the current module scope. */
predicate importedLocalName(UCODE::ImportStatement imp, string localName) {
  exists(UCODE::ImportSpecifier spec |
    spec = imp.getClause().getNamed().getChild(_) and
    (
      exists(UCODE::Identifier alias |
        alias = spec.getAlias() and localName = alias.getValue()
      )
      or
      not exists(spec.getAlias()) and
      localName = spec.getName().(UCODE::Identifier).getValue()
    )
  )
  or
  exists(UCODE::Identifier defaultImport |
    defaultImport = imp.getClause().getDefault() and
    localName = defaultImport.getValue()
  )
}

/** Direct identifier callee of a call; member and wrapped callees are not resolved. */
UCODE::Identifier calleeIdent(UCODE::CallExpression c) {
  result = c.getFunction().(UCODE::Identifier)
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

/** Global builtin `system(...)` when no same-file import binds that local name. */
class BuiltinSystemCall extends NamedCall {
  BuiltinSystemCall() {
    this.getName() = "system" and
    not exists(UCODE::ImportStatement imp |
      imp.getLocation().getFile() = this.getLocation().getFile() and
      importedLocalName(imp, "system")
    )
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
 * Conservative absence-of-shadowing check, not proof of trusted semantics.
 * Every same-file occurrence of the identifier must be a direct callee. Imports, declarations, parameters, assignments and
 * aliases all make the binding unknown, even in an unrelated lexical scope.
 * This deliberately does not infer the behavior of locally defined helpers.
 */
predicate unambiguousShellquoteCall(NamedCall sq) {
  sq.getName() = "shellquote" and
  not exists(UCODE::Identifier id |
    id.getLocation().getFile() = sq.getLocation().getFile() and
    id.getValue() = "shellquote" and
    not id = calleeIdent(any(NamedCall c))
  )
}

/**
 * Bounded command grammar: only a fixed non-interpreter command followed by
 * literal, unquoted words and whitespace. Unknown commands, shell separators,
 * substitutions, assignments, wrappers and interpreter programs stay candidates.
 * Extend this allowlist only with command semantics and regression controls.
 */
predicate supportedQuotedArgumentPrefix(UCODE::StringFragment prefix) {
  prefix.getValue().regexpMatch("[ \\t]*(swconfig|echo|printf)[ \\t]+([A-Za-z0-9_./-]+[ \\t]+)*")
}

/**
 * Necessary shape for a future barrier: an unchanged call in the first
 * substitution of a supported literal command. Both adjacent fragments must
 * establish shell-word boundaries. Quoting/backslashes in other template text
 * remain unsupported, as do local helpers or ambiguous shellquote bindings.
 */
predicate supportedShellquoteTemplateShape(RequestArgsAccess src, NamedCall sink) {
  taintReachesSink(src, sink) and
  exists(
    NamedCall sq, UCODE::TemplateSubstitution sub, UCODE::TemplateString tmpl,
    UCODE::StringFragment prefix, UCODE::StringFragment suffix
  |
    unambiguousShellquoteCall(sq) and
    src.getParent*() = sq.getArgument(0) and
    sq = sub.getChild() and
    prefix = tmpl.getChild(0) and
    sub = tmpl.getChild(1) and
    suffix = tmpl.getChild(2) and
    tmpl = sink.getArgument(_) and
    supportedQuotedArgumentPrefix(prefix) and
    suffix.getValue().regexpMatch("[ \\t].*") and
    not exists(UCODE::StringFragment frag |
      frag = tmpl.getChild(_) and frag.getValue().regexpMatch(".*[\"\\\\].*")
    )
  )
}

/**
 * No shellquote implementation currently has a trusted semantic model. Spelling
 * and absence of local declarations do not prove a builtin exists or quotes
 * safely. Retain candidates until binding and helper semantics are established.
 * Keep the shape check independently testable for that future model.
 */
predicate completeQuotedTemplateArg(RequestArgsAccess src, NamedCall sink) {
  supportedShellquoteTemplateShape(src, sink) and
  none()
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
  result.getLocation().getFile().getRelativePath() = "usr/share/ucode/luci/sys.uc" and
  result = any(UCODE::ExportStatement e).getDeclaration()
}

/** Holds if `n` is inside `init_action` in `sys.uc`. */
predicate inInitAction(UCODE::AstNode n) { n.getParent*() = initActionFn() }

/** `export function process_list` in installed luci.sys (`sys.uc`). */
UCODE::FunctionDeclaration processListFn() {
  result = functionDecl("process_list") and
  result.getLocation().getFile().getRelativePath() = "usr/share/ucode/luci/sys.uc" and
  result = any(UCODE::ExportStatement e).getDeclaration()
}

/** Holds if `n` is inside `process_list` in `sys.uc`. */
predicate inProcessList(UCODE::AstNode n) { n.getParent*() = processListFn() }

/** `export function conntrack_list` in installed luci.sys (`sys.uc`). */
UCODE::FunctionDeclaration conntrackListFn() {
  result = functionDecl("conntrack_list") and
  result.getLocation().getFile().getRelativePath() = "usr/share/ucode/luci/sys.uc" and
  result = any(UCODE::ExportStatement e).getDeclaration()
}

/** Holds if `n` is inside `conntrack_list` in `sys.uc`. */
predicate inConntrackList(UCODE::AstNode n) { n.getParent*() = conntrackListFn() }

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
