import { popen } from 'fs';
let pipe = popen('printf issue87-native', 'r');
print(pipe.read('all'), '\n'); pipe.close();
