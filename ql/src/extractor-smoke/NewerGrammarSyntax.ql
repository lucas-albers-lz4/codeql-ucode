import codeql.ucode.ast.internal.TreeSitter

from string kind, string file, int line, int column
where
  exists(UCODE::DynamicImportExpression d |
    kind = "plain-import" and
    file = d.getLocation().getFile().getBaseName() and
    line = d.getLocation().getStartLine() and
    column = d.getLocation().getStartColumn()
  )
  or exists(UCODE::ExportStatement e, UCODE::FunctionDeclaration f |
    e.getDeclaration() = f and
    kind = "plain-export" and
    file = e.getLocation().getFile().getBaseName() and
    line = e.getLocation().getStartLine() and
    column = e.getLocation().getStartColumn()
  )
  or exists(UcodeMarkup::DynamicImportExpression d |
    kind = "markup-import" and
    file = d.getLocation().getFile().getBaseName() and
    line = d.getLocation().getStartLine() and
    column = d.getLocation().getStartColumn()
  )
  or exists(UcodeMarkup::ExportStatement e, UcodeMarkup::FunctionDeclaration f |
    e.getDeclaration() = f and
    kind = "markup-export" and
    file = e.getLocation().getFile().getBaseName() and
    line = e.getLocation().getStartLine() and
    column = e.getLocation().getStartColumn()
  )
select kind, file, line, column
