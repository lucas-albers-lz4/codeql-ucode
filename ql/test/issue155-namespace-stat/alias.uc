import * as fs from 'fs';
let alias = fs;
alias.stat(path);
alias.rename(path, path + '.prev');
