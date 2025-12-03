<script>
    import { createEventDispatcher } from 'svelte';
    
    export let data = []; // [{date: '2023-01-01', value: 50}]
    export let selectedDate = null;
    export let type = 'performance'; // 'performance' | 'sleep'

    const dispatch = createEventDispatcher();
    
    let currentCursor = new Date(); // For navigation
    
    // Derived state for the view
    $: year = currentCursor.getFullYear();
    $: month = currentCursor.getMonth();
    $: monthLabel = currentCursor.toLocaleDateString('default', { month: 'long', year: 'numeric' });
    
    // Create Data Map
    $: dataMap = (data || []).reduce((acc, item) => {
        acc[item.date] = item.value;
        return acc;
    }, {});

    function prevMonth() {
        currentCursor = new Date(year, month - 1, 1);
    }

    function nextMonth() {
        currentCursor = new Date(year, month + 1, 1);
    }

    // Generate Grid
    let days = [];
    $: {
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startOffset = firstDay.getDay(); // 0 = Sunday
        const totalDays = lastDay.getDate();
        
        let grid = [];
        // Empty slots for start offset
        for(let i=0; i<startOffset; i++) grid.push(null);
        // Days
        for(let i=1; i<=totalDays; i++) {
            const d = new Date(year, month, i);
            // Local ISO string fix
            const iso = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
            grid.push({ date: iso, day: i });
        }
        days = grid;
    }

    function getColor(val) {
        if (val === undefined) return 'bg-zinc-800/30 text-zinc-600 hover:bg-zinc-800';
        
        if (type === 'performance') {
            if (val >= 80) return 'bg-emerald-500 text-black font-bold shadow-[0_0_10px_rgba(16,185,129,0.3)]';
            if (val >= 60) return 'bg-emerald-600/80 text-white';
            if (val >= 30) return 'bg-emerald-900/50 text-zinc-300 border border-emerald-900';
            return 'bg-red-900/30 text-red-400 border border-red-900/50';
        } else {
            if (val >= 420) return 'bg-violet-500 text-white shadow-[0_0_10px_rgba(139,92,246,0.3)]';
            if (val >= 300) return 'bg-violet-900/50 text-zinc-300 border border-violet-900';
            return 'bg-red-900/30 text-red-400';
        }
    }
</script>

<div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-4">
    <div class="flex justify-between items-center mb-4">
        <button on:click={prevMonth} class="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors">←</button>
        <span class="text-xs font-bold uppercase tracking-wider text-zinc-300">{monthLabel}</span>
        <button on:click={nextMonth} class="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors">→</button>
    </div>

    <div class="grid grid-cols-7 gap-1 text-center mb-2">
        {#each ['S','M','T','W','T','F','S'] as d}
            <span class="text-[9px] text-zinc-600 font-bold">{d}</span>
        {/each}
    </div>
    
    <div class="grid grid-cols-7 gap-1">
        {#each days as day}
            {#if day}
                <button 
                    on:click={() => dispatch('select', day.date)}
                    class="h-8 rounded flex items-center justify-center text-[10px] transition-all relative
                    {getColor(dataMap[day.date])}
                    {selectedDate === day.date ? 'ring-2 ring-white z-10 scale-110' : 'hover:scale-105'}"
                >
                    {day.day}
                </button>
            {:else}
                <div></div>
            {/if}
        {/each}
    </div>
</div>