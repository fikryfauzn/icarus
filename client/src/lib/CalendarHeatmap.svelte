<script>
  export let title = "Activity";
  export let data = []; // [{ date: "2025-01-01", value: 50 }, ...]
  export let type = "performance"; // 'performance' | 'sleep'

  // 1. Create a quick lookup map whenever data changes
  $: dataMap = (data || []).reduce((acc, item) => {
      acc[item.date] = item.value;
      return acc;
  }, {});

  // 2. Generate the grid structure reactively
  let grid = [];
  
  $: {
      const rows = [];
      
      // Calculate date range (Last 52 weeks)
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(endDate.getDate() - 364); // Approx 1 year
      
      // Align start date to the previous Sunday for a clean grid
      while (startDate.getDay() !== 0) {
          startDate.setDate(startDate.getDate() - 1);
      }

      let iterDate = new Date(startDate);
      
      // 53 columns (weeks)
      for (let w = 0; w < 53; w++) {
          const week = [];
          // 7 rows (days)
          for (let d = 0; d < 7; d++) {
              const iso = iterDate.toISOString().split('T')[0];
              // Safe access to the map
              const val = dataMap[iso];
              
              week.push({
                  date: iso,
                  value: val,
                  inFuture: iterDate > endDate
              });
              
              // Increment day
              iterDate.setDate(iterDate.getDate() + 1);
          }
          rows.push(week);
      }
      grid = rows;
  }

  // --- Color Logic ---
  function getColor(cell) {
      if (cell.inFuture) return 'bg-transparent border border-zinc-900/50';
      if (cell.value === undefined || cell.value === null) return 'bg-zinc-900/50';

      if (type === 'performance') {
          // Score 0-100
          if (cell.value === 0) return 'bg-zinc-900/50';
          if (cell.value < 30) return 'bg-red-900/50 border border-red-900'; // Bad day
          if (cell.value < 60) return 'bg-emerald-900/60';
          if (cell.value < 80) return 'bg-emerald-600';
          return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]'; // Ultra day
      } 
      
      if (type === 'sleep') {
          // Mins
          if (cell.value === 0) return 'bg-zinc-900/50';
          if (cell.value < 300) return 'bg-red-600'; // < 5h
          if (cell.value < 420) return 'bg-orange-500'; // < 7h
          return 'bg-violet-500'; // Good sleep
      }
  }

  function getTooltip(cell) {
      if (!cell.value) return `${cell.date}: No data`;
      if (type === 'sleep') {
          const h = Math.floor(cell.value / 60);
          const m = cell.value % 60;
          return `${cell.date}: ${h}h ${m}m`;
      }
      return `${cell.date}: Score ${cell.value}`;
  }
</script>

<div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 overflow-x-auto">
    <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-4 sticky left-0">{title}</h3>
    
    <div class="flex gap-1 min-w-max">
        {#each grid as week}
            <div class="flex flex-col gap-1">
                {#each week as day}
                    <div 
                        class="w-3 h-3 rounded-sm {getColor(day)} transition-all hover:scale-125 hover:z-10 relative group"
                    >
                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-zinc-800 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap z-20 border border-zinc-700 shadow-xl pointer-events-none font-mono">
                            {getTooltip(day)}
                        </div>
                    </div>
                {/each}
            </div>
        {/each}
    </div>
    
    <div class="flex justify-end items-center gap-2 mt-4 text-[10px] text-zinc-600">
        <span>Less</span>
        {#if type === 'performance'}
            <div class="w-2 h-2 bg-zinc-900/50 rounded-sm"></div>
            <div class="w-2 h-2 bg-red-900/50 rounded-sm"></div>
            <div class="w-2 h-2 bg-emerald-900/60 rounded-sm"></div>
            <div class="w-2 h-2 bg-emerald-400 rounded-sm"></div>
        {:else}
            <div class="w-2 h-2 bg-red-600 rounded-sm"></div>
            <div class="w-2 h-2 bg-orange-500 rounded-sm"></div>
            <div class="w-2 h-2 bg-violet-500 rounded-sm"></div>
        {/if}
        <span>More</span>
    </div>
</div>