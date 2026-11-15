import { readfile } from 'fs';
{ let readfile = function(x) { return 'shadow'; };
  printf('existing=%s\n', readfile('unused')); }
