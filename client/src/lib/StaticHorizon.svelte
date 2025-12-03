<script>
    export let sessions = [];
    export let sleep = null;
    export let date = "";

    let hoveredItem = null;

    const domainColors = {
        'Work': 'bg-emerald-500', 'Personal Project': 'bg-violet-500', 'College': 'bg-blue-500',
        'Learning': 'bg-cyan-500', 'Health': 'bg-rose-500', 'Admin': 'bg-zinc-500', 'Relationships': 'bg-amber-500'
    };

    const typeOpacity = {
        'Deep': 'opacity-100', 'Shallow': 'opacity-60', 'Maintenance': 'opacity-30', 'Recovery': 'opacity-90'
    };

    function getSessionScore(s) {
        if (!s.outcome) return 0;
        const score = (s.outcome.progress_rating * 2) + (s.outcome.focus_quality * 1.5) + (s.outcome.quality_rating * 1);
        return Math.min(100, (score / 22.5) * 100);
    }

    function getPosition(session) {
        const start = new Date(session.start_time);
        const startMins = (start.getHours() * 60) + start.getMinutes();
        const duration = session.duration_minutes || 60;
        
        const left = (startMins / 1440) * 100;
        const width = (duration / 1440) * 100;
        return { left: `${left}%`, width: `${Math.max(0.5, width)}%` };
    }

    function getSleepPosition(s) {
        if (!s) return null;
        const start = new Date(s.sleep_start);
        const end = new Date(s.sleep_end);
        const startMins = (start.getHours() * 60) + start.getMinutes();
        let dur = (end - start) / 1000 / 60;
        if (dur < 0) dur += 1440; 

        return { 
            left: `${(startMins / 1440) * 100}%`, 
            width: `${(dur / 1440) * 100}%` 
        };
    }

    function formatTime(iso) {
        if (!iso) return '';
        return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
</script>

<div class="w-full h-full bg-[#0c0c0e] border border-zinc-800 rounded-xl p-0 relative overflow-hidden flex flex-col shadow-inner group/chart">
    
    <div class="absolute top-4 left-6 right-6 flex justify-between items-start z-20 pointer-events-none">
        <div class="flex flex-col">
            <h3 class="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">Temporal Horizon</h3>
            <div class="flex items-center gap-2 mt-1">
                <span class="text-[9px] text-zinc-600 font-mono">Top: Output</span>
                <span class="text-[9px] text-zinc-700 font-mono">|</span>
                <span class="text-[9px] text-zinc-600 font-mono">Bottom: Bio-Cost & Sleep</span>
            </div>
        </div>

        <div class="absolute left-1/2 -translate-x-1/2 top-0 pointer-events-none z-[100]">
            {#if hoveredItem}
                <div class="bg-zinc-900/95 backdrop-blur-md border border-zinc-700 px-4 py-2 rounded-lg shadow-2xl flex gap-6 animate-in fade-in zoom-in-95 duration-100 mt-4">
                    {#if hoveredItem.type === 'session'}
                        {@const s = hoveredItem.data}
                        {@const score = getSessionScore(s)}
                        <div class="flex flex-col">
                            <span class="text-[9px] text-zinc-500 uppercase font-bold">Project</span>
                            <span class="text-xs font-bold text-white whitespace-nowrap">{s.context.project_name}</span>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-[9px] text-zinc-500 uppercase font-bold">Time</span>
                            <span class="text-xs font-mono text-zinc-300">{formatTime(s.start_time)}</span>
                        </div>
                        {#if s.outcome}
                            <div class="flex flex-col">
                                <span class="text-[9px] text-zinc-500 uppercase font-bold">Score</span>
                                <span class="text-xs font-mono text-emerald-400">{Math.round(score)}</span>
                            </div>
                        {/if}
                    {:else if hoveredItem.type === 'sleep'}
                        {@const sl = hoveredItem.data}
                        <div class="flex flex-col">
                            <span class="text-[9px] text-zinc-500 uppercase font-bold">Bio-Input</span>
                            <span class="text-xs font-bold text-violet-300">Sleep Protocol</span>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-[9px] text-zinc-500 uppercase font-bold">Quality</span>
                            <span class="text-xs font-mono text-white">{sl.sleep_quality}/5</span>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    <div class="relative flex-1 w-full mt-4">
        <div class="absolute top-[70%] left-0 right-0 h-px bg-zinc-700 z-10"></div>
        
        <div class="absolute inset-0 flex pointer-events-none">
            {#each [0, 4, 8, 12, 16, 20, 24] as hour}
                <div class="relative flex-1 border-r border-zinc-800/30 h-full">
                    <span class="absolute bottom-2 -right-3 text-[9px] text-zinc-700 font-mono">{hour.toString().padStart(2, '0')}:00</span>
                </div>
            {/each}
        </div>

        <div class="absolute inset-0 mx-[2px]"> 
            {#if sleep}
                {@const pos = getSleepPosition(sleep)}
                {#if pos}
                    <div 
                        class="absolute top-[70%] bottom-0 z-0 bg-violet-500/10 border-x border-violet-500/20 hover:bg-violet-500/20 transition-colors cursor-crosshair"
                        style="left: {pos.left}; width: {pos.width};"
                        on:mouseenter={() => hoveredItem = { type: 'sleep', data: sleep }}
                        on:mouseleave={() => hoveredItem = null}
                    >
                        <div class="absolute top-0 left-0 right-0 h-0.5 bg-violet-500/50"></div>
                    </div>
                {/if}
            {/if}

            {#each sessions as s}
                {@const pos = getPosition(s)}
                {@const score = getSessionScore(s)}
                {@const color = domainColors[s.context.domain] || 'bg-zinc-500'}
                {@const opacity = typeOpacity[s.context.work_type] || 'opacity-100'}
                
                {#if s.outcome}
                    {@const stress = s.after?.stress || 0}
                    {@const stressHeight = (stress / 10) * 25}
                    {@const stressColor = stress > 7 ? 'bg-red-500' : stress > 4 ? 'bg-orange-500/80' : 'bg-zinc-700/50'}
                    <div class="absolute top-[70%] rounded-b-[2px] {stressColor} transition-all border-x border-white/5 pointer-events-none z-10 mix-blend-hard-light" style="left: {pos.left}; width: {pos.width}; height: {stressHeight}%;"></div>
                {/if}

                <div 
                    class="absolute bottom-[30%] group transition-all duration-300 hover:z-50 cursor-pointer z-20"
                    style="left: {pos.left}; width: {pos.width}; height: {s.outcome ? (score * 0.7) : 40}%;"
                    on:mouseenter={() => hoveredItem = { type: 'session', data: s }}
                    on:mouseleave={() => hoveredItem = null}
                >
                    <div class="w-full h-full rounded-t-[2px] {color} {opacity} border-t border-x border-white/10 bg-gradient-to-b from-white/10 to-transparent backdrop-blur-[1px] hover:brightness-125 shadow-[0_-4px_15px_rgba(0,0,0,0.3)]"></div>
                </div>
            {/each}
        </div>
    </div>
</div>