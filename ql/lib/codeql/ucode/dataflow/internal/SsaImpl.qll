private import ucode
private import codeql.ucode.controlflow.BasicBlocks as BasicBlocks
private import BasicBlocks
private import codeql.ucode.controlflow.ControlFlowGraph
private import codeql.ssa.Ssa as SsaImplCommon

/**
 * Holds if CFG node `n` is a statement (or other leaf) that contains AST node `inner`.
 *
 * Wrapper CFG still treats statements as leaves, so SSA is statement-level:
 * a write/read is attributed to the enclosing CFG node, not the identifier token.
 */
private predicate cfgNodeContains(CfgNode n, AstNode inner) {
  inner.getParent*() = n.getAstNode()
}

module SsaInput implements SsaImplCommon::InputSig<Location> {
  class BasicBlock = BasicBlocks::BasicBlock;

  class ControlFlowNode = CfgNode;

  class ExitBasicBlock = BasicBlocks::ExitBasicBlock;

  BasicBlock getImmediateBasicBlockDominator(BasicBlock bb) { result = bb.getImmediateDominator() }

  BasicBlock getABasicBlockSuccessor(BasicBlock bb) { result = bb.getASuccessor() }

  /**
   * A variable amenable to SSA construction.
   */
  class SourceVariable extends Variable {
    SourceVariable() { exists(this.getAnAccess()) }
  }

  predicate variableWrite(BasicBlock bb, int i, SourceVariable v, boolean certain) {
    cfgNodeContains(bb.getNode(i), v.getAstNode()) and
    certain = true
  }

  predicate variableRead(BasicBlock bb, int i, SourceVariable v, boolean certain) {
    exists(VariableReadAccess va |
      va.getVariable() = v and
      cfgNodeContains(bb.getNode(i), va.getAstNode())
    ) and
    certain = true
  }
}

import SsaImplCommon::Make<Location, SsaInput> as Impl

class Definition = Impl::Definition;

class WriteDefinition = Impl::WriteDefinition;

class UncertainWriteDefinition = Impl::UncertainWriteDefinition;

class PhiDefinition = Impl::PhiNode;

module Consistency = Impl::Consistency;

/** Holds if `v` is read at index `i` in basic block `bb`. */
private predicate variableReadActual(BasicBlock bb, int i, Variable v) {
  SsaInput::variableRead(bb, i, v, true)
}

cached
private module Cached {
  cached
  CfgNode getARead(Definition def) {
    exists(Variable v, BasicBlock bb, int i |
      Impl::ssaDefReachesRead(v, def, bb, i) and
      variableReadActual(bb, i, v) and
      result = bb.getNode(i)
    )
  }

  cached
  predicate firstRead(Definition def, CfgNode read) {
    exists(BasicBlock bb1, int i1, BasicBlock bb2, int i2 |
      def.definesAt(_, bb1, i1) and
      Impl::adjacentDefRead(def, bb1, i1, bb2, i2) and
      variableReadActual(bb2, i2, _) and
      read = bb2.getNode(i2)
    )
  }

  /**
   * Holds if `v` is written at index `i` in basic block `bb`, and the corresponding
   * write access node in the CFG is `write`.
   */
  cached
  predicate variableWriteActual(BasicBlock bb, int i, Variable v, CfgNode write) {
    write = bb.getNode(i) and
    SsaInput::variableWrite(bb, i, v, true)
  }
}

import Cached
