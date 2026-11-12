import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.Diagnostics
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.m3.Models

/**
 * M1 surface. Generated AST wrappers, CFG, and dataflow remain in-tree but are
 * not imported here: the generator scaffolding does not compile (lowercase
 * `ucodeFile`, leftover bicep imports, overlapping mapping-bucket classes).
 * M3 queries will re-export a bounded subset once those wrappers are patched.
 */
