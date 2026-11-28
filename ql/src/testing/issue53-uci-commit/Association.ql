/** @name Source-declared UCI commit association identities
 * @kind table
 * @id test/issue53-uci-commit/association
 */
import codeql.ucode.Concepts
from SourceDeclaredUciCommit c
select c.getLocation().getFile().getRelativePath(), c, c.getImport(), c.getSpecifier(),
  c.getReceiverDeclaration(), c.getInitializer(), c.getReceiver(), c.getConfigArgument()
