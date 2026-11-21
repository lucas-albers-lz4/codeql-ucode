/**
 * @name Template string AST CFG membership
 * @description Reports whether each named template AST node has incoming and
 *              outgoing control-flow edges. This is statement/evaluation CFG
 *              membership, not a value node.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-cfg-nodes
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.CFG
import codeql.ucode.controlflow.CfgNodes
private import codeql.ucode.ast.internal.AstNodes

private predicate isTargetTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

private string incomingStatus(AstCfgNode node) {
  result = "incoming" and exists(CfgNode pred | pred.getASuccessor() = node)
  or
  result = "no incoming" and not exists(CfgNode pred | pred.getASuccessor() = node)
}

private string outgoingStatus(AstCfgNode node) {
  result = "outgoing" and exists(CfgNode succ | node.getASuccessor() = succ)
  or
  result = "no outgoing" and not exists(CfgNode succ | node.getASuccessor() = succ)
}

from TemplateString template, AstCfgNode node
where
  isTargetTemplate(template) and
  toTreeSitter(node.getAstNode()) = toTreeSitter(template)
select node,
  "template AstCfgNode at " + template.getLocation().getStartLine().toString() + ":" +
    template.getLocation().getStartColumn().toString() + " " + incomingStatus(node) + " and " +
    outgoingStatus(node)
