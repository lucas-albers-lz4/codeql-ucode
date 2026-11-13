/**
 * Provides classes and predicates for defining flow summaries.
 *
 * Language adapter for `codeql/dataflow` 1.1.6. Generator leftovers used Rust
 * types (`Function`, `CallExprBase`, `SourceElement`) that ucode does not have.
 * Summaries compile; they do not attach to calls (`getACall` is `none()`, and
 * `viableLibraryCallable` stays `none()`). Not production taint and not
 * `path_found`.
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
   * add `storeStep` / `readStep` or attach summaries to calls.
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
   * No library-call resolution. `viableSourceCallable` / `viableLibraryCallable`
   * stay `none()`. Summaries typecheck but do not apply to source calls.
   */
  DataFlowCall getACall(Impl::Public::SummarizedCallable sc) { none() }
}

module Private {
  import Impl::Private

  module Steps = Impl::Private::Steps<StepsInput>;
}

module Public = Impl::Public;
