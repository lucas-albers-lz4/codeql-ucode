private import ucode
private import codeql.ucode.controlflow.BasicBlocks as BasicBlocks
private import BasicBlocks
private import codeql.ucode.controlflow.ControlFlowGraph
private import codeql.ssa.Ssa as SsaImplCommon
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

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
    (
      bb.getNode(i).getAstNode() = v.getAstNode()
      or
      exists(VariableWriteAccess va, UCODE::Identifier ident, UCODE::AstNode operation |
        va.getVariable() = v and
        va.getAstNode() = TIdentifier(ident) and
        (
          operation.(UCODE::AssignmentExpression).getLeft() = ident or
          operation.(UCODE::AugmentedAssignmentExpression).getLeft() = ident or
          operation.(UCODE::UpdateExpression).getArgument() = ident
        ) and
        toTreeSitter(bb.getNode(i).getAstNode()) = operation and
        (
          not operation instanceof UCODE::AugmentedAssignmentExpression
          or
          exists(UCODE::AugmentedAssignmentExpression a |
            operation = a and
            (
              a.getOperator() in ["&&=", "||=", "??="] and
              bb.getNode(i).getAstNode() = TExpression(a)
              or
              not a.getOperator() in ["&&=", "||=", "??="] and
              bb.getNode(i).getAstNode() = TAugmentedAssignmentExpression(a)
            )
          )
        )
      )
      or
      exists(UCODE::ForInStatement f, UCODE::Identifier ident |
        bb.getNode(i).getAstNode() = TStatement(f) and
        (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue()) and
        (
          v.getAstNode() = TIdentifier(ident)
          or
          exists(VariableWriteAccess wa |
            wa.getVariable() = v and wa.getAstNode() = TIdentifier(ident)
          )
        )
      )
      or
      exists(UCODE::ForInAltStatement f, UCODE::Identifier ident |
        bb.getNode(i).getAstNode() = TStatement(f) and
        (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue()) and
        (
          v.getAstNode() = TIdentifier(ident)
          or
          exists(VariableWriteAccess wa |
            wa.getVariable() = v and wa.getAstNode() = TIdentifier(ident)
          )
        )
      )
      or
      exists(UCODE::CatchClause c, UCODE::Identifier ident |
        bb.getNode(i).getAstNode() = TCatchClause(c) and
        ident = c.getParameter() and
        v.getAstNode() = TIdentifier(ident)
      )
    ) and
    certain = true
  }

  predicate variableRead(BasicBlock bb, int i, SourceVariable v, boolean certain) {
    exists(VariableReadAccess va |
      va.getVariable() = v and
      bb.getNode(i).getAstNode() = va.getAstNode()
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

/** A source definition can reach a read through zero or more phi joins. */
predicate writeReachesRead(WriteDefinition def, CfgNode read) {
  read = getARead(def)
  or
  exists(PhiDefinition phi | phiInput+(def, phi) and read = getARead(phi))
}

private predicate phiInput(Definition input, Definition phi) {
  Impl::phiHasInputFromBlock(phi.(PhiDefinition), input, _)
}
