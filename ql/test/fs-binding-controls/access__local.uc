import { access } from 'fs';
{ let access = function(x) { return 'shadow'; }; printf('local=%s\n', access("fixtures/native.txt"));
}
