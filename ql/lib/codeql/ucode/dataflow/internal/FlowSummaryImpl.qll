/**
 * Provides classes and predicates for defining flow summaries.
 *
 * Language adapter for `codeql/dataflow` 1.1.6. Generator leftovers used Rust
 * types (`Function`, `CallExprBase`, `SourceElement`) that ucode does not have.
 * `getACall` matches identifier callees (`system`, `popen`, `shellquote`) to
 * string-keyed summaries. Member callees have no identifier. `Future` stays
 * `none()`. Builtin identifier `system` and imported `'fs'` `popen`
 * / `basename` may resolve as `viableLibraryCallable` separately.
 * `propagatesFlow` stays `none()`.
 * Does not wire summary steps into `localFlowStep`. Not production taint
 * and not `path_found`.
 */

private import ucode
private import codeql.dataflow.internal.FlowSummaryImpl
private import codeql.dataflow.internal.AccessPathSyntax as AccessPath
private import codeql.ucode.dataflow.internal.DataFlowImplSpecific as DataFlowImplSpecific
private import DataFlowImplSpecific::Private
private import codeql.ucode.dataflow.FlowSummary

module Input implements InputSig<Location, DataFlowImplSpecific::UcodeDataFlow> {
  /**
   * MaD summary keys are strings. No canonical-path / crate resolution yet.
   */
  class SummarizedCallableBase = string;

  DataFlowImplSpecific::UcodeDataFlow::ReturnKind getStandardReturnValueKind() {
    result instanceof NormalReturnKind
  }

  string encodeParameterPosition(ParameterPosition pos) {
    exists(int i | pos.isPositional(i) and result = i.toString())
  }

  string encodeArgumentPosition(DataFlowImplSpecific::UcodeDataFlow::ArgumentPosition pos) {
    exists(int i | pos.isPositional(i) and result = i.toString())
  }

  /**
   * MaD `Field[name]` and `Element` tokens from inhabited `TContent`.
   * `Future` stays `none()`: ucode has no async/future AST. Does not
   * add `storeStep` / `readStep` or summary steps into `localFlowStep`.
   */
  string encodeContent(DataFlowImplSpecific::UcodeDataFlow::ContentSet cs, string arg) {
    exists(DataFlowImplSpecific::UcodeDataFlow::Content c |
      cs.isSingleton(c) and
      (
        c = TFieldContent(arg) and result = "Field"
        or
        c = TElementContent() and result = "Element" and arg = ""
      )
    )
  }

  bindingset[token]
  ParameterPosition decodeUnknownParameterPosition(AccessPath::AccessPathTokenBase token) {
    // Needed to support `Argument[x..y]` ranges.
    token.getName() = "Argument" and
    result.isPositional(AccessPath::parseInt(token.getAnArgument()))
  }

  bindingset[token]
  DataFlowImplSpecific::UcodeDataFlow::ArgumentPosition decodeUnknownArgumentPosition(
    AccessPath::AccessPathTokenBase token
  ) {
    // Needed to support `Parameter[x..y]` ranges.
    token.getName() = "Parameter" and
    result.isPositional(AccessPath::parseInt(token.getAnArgument()))
  }
}

private import Make<Location, DataFlowImplSpecific::UcodeDataFlow, Input> as Impl

private module StepsInput implements Impl::Private::StepsInputSig {
  /**
   * Identifier callees whose name equals summarized callable `sc`.
   * Member, subscript, parenthesized, and nested-call callees have no
   * `getIdentifier`, so they have no result. No async/future calls:
   * ucode has no async AST. Builtin identifier `system` and imported
   * `'fs'` `popen` / `basename` may resolve as `viableLibraryCallable`
   * separately. Frameworks `getACall` keys stay `system` / `popen` /
   * `shellquote`.
   * Unique same-file identifier
   * and member-property FunctionDeclarations may resolve separately.
   * Member `getACall` stays empty. Does not wire summary steps into
   * `localFlowStep`.
   */
  DataFlowCall getACall(Impl::Public::SummarizedCallable sc) {
    exists(CallExpression c |
      c.getIdentifier().getName() = sc and
      result.asCall().getCall() = c
    )
  }
}

/**
 * Identifier-callee `getACall` for extractor-smoke. Same relation as
 * `StepsInput`. Not production taint.
 */
module IdentifierCalls {
  DataFlowCall getACall(Impl::Public::SummarizedCallable sc) {
    result = StepsInput::getACall(sc)
  }
}

module Private {
  import Impl::Private

  module Steps = Impl::Private::Steps<StepsInput>;
}

module Public = Impl::Public;
