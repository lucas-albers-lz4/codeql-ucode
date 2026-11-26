/** @name Testing-only namespace stat class membership
 * @description Verify model membership independently of argument projection.
 * @kind table
 * @id ucode/testing/issue155-namespace-stat-class
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models

from SourceDeclaredFsNamespaceStatCall call
select call.getLocation().getFile().getBaseName() as path, call as call_node
