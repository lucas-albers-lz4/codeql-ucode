import { basename } from 'fs';
{ let basename = function(x) { return 'shadow'; }; printf('local=%s\n', basename('/a/fs-native'));
}
