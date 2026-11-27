import { cursor } from 'uci';
function run() { let ctx = cursor(); { function ctx() {} ctx.commit('ok'); } }
