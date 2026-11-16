// Static AST inventory. Never executes frontend modules.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from '../../../../frontend/node_modules/typescript/lib/typescript.js';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(base,'../../..');
const sources=JSON.parse(fs.readFileSync(path.join(base,'evidence/source_files.json'),'utf8'));
const rows=[];
for(const {file} of sources){
 if(!/\.tsx?$/.test(file))continue;
 const text=fs.readFileSync(path.join(root,file),'utf8');
 const sf=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,file.endsWith('tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
 function visit(node,scope=[]){
  let childScope=scope;
  if(ts.isFunctionDeclaration(node)||ts.isMethodDeclaration(node)||ts.isArrowFunction(node)||ts.isFunctionExpression(node)){
   const parent=node.parent;
   const own=node.name?.getText(sf)||(ts.isVariableDeclaration(parent)||ts.isPropertyAssignment(parent)?parent.name.getText(sf):null);
   const line=sf.getLineAndCharacterOfPosition(node.getStart(sf)).line+1;
   const name=own||`callback@${line}`;
   const full=[...scope,name].join('.');
   const start=node.getStart(sf),end=node.end;
   const calls=[],guards=[];
   function bodyScan(n){if(n!==node&&(ts.isFunctionDeclaration(n)||ts.isArrowFunction(n)||ts.isFunctionExpression(n)))return;if(ts.isCallExpression(n))calls.push(n.expression.getText(sf));if(ts.isThrowStatement(n)||ts.isIfStatement(n))guards.push(n.getText(sf).slice(0,250));ts.forEachChild(n,bodyScan)}
   bodyScan(node);
   rows.push({function:full,file,line,end_line:sf.getLineAndCharacterOfPosition(end).line+1,inputs:node.parameters.map(p=>p.getText(sf)).join(', '),returns:node.type?.getText(sf)||'Inferido por TypeScript / JSX',calls:[...new Set(calls)],guards,kind:ts.SyntaxKind[node.kind],jsdoc:node.jsDoc?.map(d=>d.comment).filter(Boolean).join(' ')||null});
   childScope=[...scope,name];
  }
  ts.forEachChild(node,n=>visit(n,childScope));
 }
 visit(sf);
}
fs.writeFileSync(path.join(base,'evidence/typescript_functions.json'),JSON.stringify(rows,null,2));
console.log(`TypeScript AST: ${rows.length} functions, methods and callbacks`);
