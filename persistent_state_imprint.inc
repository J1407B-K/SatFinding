void Solver::ps_hook(){
 static bool done=false;
 if(done || conflicts!=660) return;
 if(qhead!=trail.size()) exit(70);
 ah_mode=lt_run;ah_dir=lt_dir;
 lt_snapshot("ps_before");ah_dump("before");
 if(lt_run!="A" && lt_run!="B" && lt_run!="B_REMOVE_L2"){
  FILE* f=fopen((lt_dir+"/A.before.allowed.bin").c_str(),"rb");if(!f)exit(70);
  auto aa=ah_read<double>(f);auto hh=ah_read<int>(f);auto ii=ah_read<int>(f);fclose(f);
  bool activity_only=lt_run=="B_REMOVE_L2_ACTIVITY_RESET",heap_only=lt_run=="B_REMOVE_L2_HEAP_RESET";
  vec<double> candidate;activity.copyTo(candidate);
  if(!heap_only){if(aa.size()!=(size_t)activity.size())exit(70);for(int v=0;v<candidate.size();++v)candidate[v]=aa[v];}
  vec<int> hv,iv;
  if(activity_only)order_heap.ah_copy(hv,iv);else {for(int v:hh)hv.push(v);for(int v:ii)iv.push(v);}
  Heap<VarOrderLt> probe((VarOrderLt(candidate)));probe.ah_restore(hv,iv);
  int missing=0;for(int v=0;v<nVars();++v)if(value(v)==l_Undef&&decision[v]&&!probe.inHeap(v))++missing;
  FILE* audit=fopen((lt_dir+"/"+lt_run+".legality.json").c_str(),"w");
  fprintf(audit,"{\"heap_valid\":%s,\"missing_eligible\":%d,\"before_mutation\":true}\n",probe.ah_valid()?"true":"false",missing);fclose(audit);
  if(!probe.ah_valid()||missing){fprintf(stderr,"Candidate illegal: heap_valid=%d missing_eligible=%d\n",probe.ah_valid(),missing);exit(71);}
  if(!heap_only)for(int v=0;v<activity.size();++v)activity[v]=aa[v];
  if(!activity_only)order_heap.ah_restore(hv,iv);
 }
 ah_dump("after");lt_snapshot("ps_after");done=true;
}
