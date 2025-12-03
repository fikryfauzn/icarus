<script>
    import { createEventDispatcher, onDestroy, onMount } from 'svelte';
    import { post } from './api';

    export let session;
    const dispatch = createEventDispatcher();

    let now = new Date();
    let elapsed = 0;
    let timer;
    let scratchpadText = "";
    let inputRef; // Reference to the input for autofocus

    // Calculate progress based on planned duration
    $: planned = session.context.planned_duration_min || 60;
    $: progress = Math.min(100, (elapsed / (planned * 60)) * 100);
    $: isOvertime = elapsed > (planned * 60);

    onMount(() => {
        timer = setInterval(() => {
            now = new Date();
            const start = new Date(session.start_time);
            elapsed = Math.floor((now - start) / 1000); 
        }, 1000);
        
        // Instant focus lock
        if(inputRef) inputRef.focus();
    });

    onDestroy(() => clearInterval(timer));

    function formatTime(totalSeconds) {
        if (isNaN(totalSeconds)) return "00:00";
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    async function submitScratchpad() {
        if (!scratchpadText.trim()) return;

        // Send to Quick Capture endpoint
        await post('/tasks', {
            domain: session.context.domain,
            project_name: "Quick Capture",
            activity_description: scratchpadText,
            work_type: "Shallow"
        });
        
        scratchpadText = ""; 
    }

    async function handleScratchpadKey(e) {
        // Submit on Enter OR Ctrl+Enter
        if ((e.key === 'Enter' && !e.shiftKey) || (e.key === 'Enter' && e.ctrlKey)) {
            e.preventDefault();
            submitScratchpad();
        }
    }

    function handleGlobalKeys(e) {
        if (e.key === 'Escape') {
            dispatch('minimize');
        }
    }
</script>

<svelte:window on:keydown={handleGlobalKeys} />

<div class="fixed inset-0 z-50 bg-[#09090b]/95 backdrop-blur-xl flex flex-col items-center justify-center p-8 animate-in fade-in duration-300">
    
    <div class="absolute top-8 left-8 right-8 flex justify-between items-start text-zinc-500">
        <div class="flex flex-col">
            <span class="text-xs uppercase tracking-[0.2em] font-bold">Flight In Progress</span>
            <div class="flex items-center gap-2 mt-1">
                <span class="text-emerald-500 font-mono text-xs px-2 py-0.5 bg-emerald-500/10 rounded border border-emerald-500/20">{session.context.domain}</span>
                <span class="text-zinc-400 font-mono text-xs">{session.context.work_type}</span>
            </div>
        </div>
        <div class="flex flex-col items-end gap-1">
            <button on:click={() => dispatch('minimize')} class="hover:text-white transition-colors text-xs uppercase tracking-widest border border-zinc-700 px-3 py-1 rounded">
                Minimize [ESC]
            </button>
        </div>
    </div>

    <div class="w-full max-w-4xl text-center space-y-12">
        
        <div class="space-y-4">
            <h2 class="text-zinc-500 text-sm uppercase tracking-widest font-bold">Current Objective</h2>
            <h1 class="text-4xl md:text-6xl font-bold text-white tracking-tight leading-tight">
                {session.context.project_name}
            </h1>
            <p class="text-xl text-zinc-400 font-light">{session.context.activity_description}</p>
        </div>

        <div class="relative inline-flex items-center justify-center">
            <svg class="w-64 h-64 transform -rotate-90">
                <circle cx="128" cy="128" r="120" stroke="currentColor" stroke-width="2" fill="transparent" class="text-zinc-800" />
                <circle cx="128" cy="128" r="120" stroke="currentColor" stroke-width="4" fill="transparent" 
                    stroke-dasharray={2 * Math.PI * 120} 
                    stroke-dashoffset={(2 * Math.PI * 120) * (1 - progress / 100)}
                    class="{isOvertime ? 'text-red-500' : 'text-emerald-500'} transition-all duration-1000" />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center flex-col">
                <span class="text-6xl font-mono font-bold {isOvertime ? 'text-red-400' : 'text-white'}">
                    {formatTime(elapsed)}
                </span>
                {#if isOvertime}
                    <span class="text-xs text-red-500 uppercase font-bold tracking-widest mt-2 animate-pulse">Overtime</span>
                {:else}
                    <span class="text-xs text-zinc-500 uppercase font-bold tracking-widest mt-2"> / {planned} min</span>
                {/if}
            </div>
        </div>
    </div>

    <div class="absolute bottom-12 left-0 right-0 flex justify-center items-end gap-12 px-12">
        <div class="w-full max-w-md relative group">
            <div class="absolute -top-6 left-0 text-[10px] uppercase text-zinc-600 font-bold tracking-wider group-focus-within:text-emerald-500 transition-colors">Tactical Buffer</div>
            <input 
                bind:this={inputRef}
                bind:value={scratchpadText}
                on:keydown={handleScratchpadKey}
                class="w-full bg-transparent border-b border-zinc-700 text-zinc-300 py-2 focus:outline-none focus:border-emerald-500 transition-colors font-mono text-sm"
                placeholder="Distraction capture..."
            />
        </div>

        <button 
            on:click={() => dispatch('end')}
            class="bg-zinc-800 hover:bg-emerald-600 hover:text-white text-zinc-400 px-8 py-3 rounded-lg font-bold uppercase tracking-widest transition-all shadow-lg border border-zinc-700"
        >
            Disengage
        </button>
    </div>
</div>