/** @name Testing-only template interpolation flow foundation
 * @description Experimental local taint edge for request interpolation to one fs.stat template argument.
 * @kind table
 * @id ucode/testing/issue155-template-flow
 * @tags testing
 */
import codeql.ucode.testing.Issue155TemplateFlow
import codeql.ucode.ast.Calls
import codeql.ucode.ast.Misc
import codeql.ucode.DataFlow
import codeql.ucode.ast.internal.TreeSitter

from DataFlow::Node source, DataFlow::TemplateStringArgumentNode argument,
  CallExpression call, UCODE::Identifier formal, UCODE::ImportSpecifier specifier,
  DataFlow::Node edgeSource, TemplateSubstitution substitution
where issue155TemplateFlowRow(true, source, argument, call, formal, specifier,
  edgeSource, substitution)
select source.getLocation().getFile().getRelativePath() as path,
  source as source_node, argument as template_argument_node, call as call_node,
  formal as request_formal_node, specifier as stat_import_specifier_node,
  edgeSource as interpolation_edge_source_node, substitution as template_substitution_node,
  source.getLocation().getStartLine() as source_line,
  argument.getLocation().getStartLine() as template_line,
  call.getLocation().getStartLine() as call_line
