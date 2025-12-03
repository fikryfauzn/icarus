<script>
  import { onMount } from 'svelte';
  import { get } from './api';

  // --- State ---
  let dailyScore = 0;
  let extendedDailyScore = 0; // <-- ADD THIS
  let patterns = {}; 
  let chronotype = {}; 
  let energyLedger = {}; 
  let sleepVsWork = []; 
  let dailyIntakes = []; // <-- ADD THIS for intake calculation
  
  let loading = true;
  let range = 'week'; // 'day', 'week', 'month'

  // --- Reactive Loader ---
  $: if (range) loadData();

  async function loadData() {
    loading = true;
    try {
        const { start, end } = getDateRange(range);
        const qs = `?start=${start}&end=${end}`;

        // Fetch everything in parallel
        const [chronoRes, ledgerRes, svdRes, scoreRes, patternRes] = await Promise.all([
            get(`/analytics/chronotype${qs}`),
            get(`/analytics/energy-ledger${qs}`),
            get(`/sleep-vs-deepwork${qs}`),
            get(`/analytics/score${qs}`),
            get(`/analytics/patterns${qs}`)
        ]);

        chronotype = chronoRes;
        energyLedger = ledgerRes;
        sleepVsWork = svdRes;
        dailyScore = scoreRes.score || 0;
        patterns = patternRes;
        
        // Fetch intake data for the range and calculate extended score
        await loadIntakeData(start, end);

    } catch (e) {
        console.error("Analytics load error:", e);
    } finally {
        loading = false;
    }
  }
  
  async function loadIntakeData(start, end) {
    try {
        // Get all dates in range
        const dates = getDaysBetween(start, end);
        
        // Fetch intake for each date
        const intakePromises = dates.map(date => 
            get(`/intake?date=${date}`).catch(() => null)
        );
        dailyIntakes = await Promise.all(intakePromises);
        
        // Calculate average intake points
        const totalIntakePoints = dailyIntakes.reduce((sum, intake) => {
            return sum + (intake ? calculateIntakePoints(intake) : 0);
        }, 0);
        const avgIntakePoints = dailyIntakes.length > 0 ? totalIntakePoints / dailyIntakes.length : 0;
        
        // Calculate extended score
        extendedDailyScore = Math.min(100, Math.round(dailyScore + avgIntakePoints));
        
    } catch (e) {
        console.error("Error loading intake data:", e);
        extendedDailyScore = dailyScore;
    }
  }
  
  function calculateIntakePoints(intake) {
    if (!intake) return 0;
    let points = 0;
    
    // Water: 1 point per 2 glasses, max 5 points (10 glasses)
    points += Math.min(5, Math.floor(intake.water_count / 2));
    
    // Meals: 5 points per meal logged, max 15 points (3 meals)
    const mealsLogged = [intake.breakfast_time, intake.lunch_time, intake.dinner_time].filter(Boolean).length;
    points += mealsLogged * 5;
    
    // Cap intake points at 20 (20% of total score)
    return Math.min(20, points);
  }
  
  function getDaysBetween(start, end) {
    const dates = [];
    let current = new Date(start);
    const endDate = new Date(end);
    
    while (current <= endDate) {
      dates.push(current.toISOString().split('T')[0]);
      current.setDate(current.getDate() + 1);
    }
    return dates;
  }

  function getDateRange(r) {
      const e = new Date();
      const s = new Date();
      
      if (r === 'day') {
          // just today
      } else if (r === 'week') {
          s.setDate(e.getDate() - 6);
      } else if (r === 'month') {
          s.setDate(e.getDate() - 29);
      }
      
      return {
          start: s.toISOString().split('T')[0],
          end: e.toISOString().split('T')[0]
      };
  }

  // --- Visual Helpers ---
  function getHeatColor(score) {
    if (score === 0) return 'bg-zinc-800/50 text-zinc-600';
    if (score < 2) return 'bg-red-900/20 text-red-400';
    if (score < 3) return 'bg-orange-900/20 text-orange-400';
    if (score < 4) return 'bg-blue-900/20 text-blue-400';
    return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]';
  }

  function getLedgerStyle(val) {
    const maxVal = 3; 
    const absVal = Math.min(Math.abs(val), maxVal);
    if (val === 0) return `width: 2px; background-color: #52525b;`; 
    const percent = (absVal / maxVal) * 100;
    if (val > 0) return `width: ${percent}%; background-color: #10b981;`; 
    return `width: ${percent}%; background-color: #ef4444;`; 
  }

  function scaleY(mins, maxMins) {
    if (!mins) return 0;
    return (mins / maxMins) * 100;
  }
  
  function fmtDate(iso) {
    const d = new Date(iso);
    return `${d.getDate()}`;
  }
  
  function getMonthName(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short' });
  }
</script>

<div class="space-y-6 animate-in fade-in duration-500 pb-12">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 class="text-xl font-bold text-white">Analytics</h2>
        
        <div class="bg-zinc-900 border border-zinc-800 p-1 rounded-lg flex gap-1 w-full sm:w-auto">
            {#each ['day', 'week', 'month'] as r}
                <button 
                    on:click={() => range = r}
                    class="px-4 py-1.5 rounded-md text-xs uppercase font-bold transition-all flex-1 sm:flex-none text-center {range === r ? 'bg-zinc-700 text-white shadow' : 'text-zinc-500 hover:text-zinc-300'}"
                >
                    {r}
                </button>
            {/each}
        </div>
    </div>

    {#if loading}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="h-48 bg-zinc-900/30 rounded-xl animate-pulse"></div>
            <div class="lg:col-span-2 h-48 bg-zinc-900/30 rounded-xl animate-pulse"></div>
        </div>
        <div class="h-64 bg-zinc-900/30 rounded-xl animate-pulse"></div>
    {:else}

    <!-- Performance Index & Session DNA - FIXED GRID -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Performance Index -->
        <div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 flex flex-col justify-between">
            <div>
                <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Performance Index</h3>
                <div class="flex items-end gap-2">
                    <span class="text-5xl md:text-6xl font-black tracking-tighter text-white">{extendedDailyScore}</span>
                    <span class="text-zinc-500 text-lg mb-2">/100</span>
                </div>
                <div class="text-xs text-zinc-400 mt-2 flex items-center gap-2">
                    <span>Base: {dailyScore}</span>
                    {#if extendedDailyScore > dailyScore}
                        <span class="text-cyan-400">+{Math.round(extendedDailyScore - dailyScore)} from intake</span>
                    {/if}
                </div>
            </div>
            <div>
                <div class="mt-4 h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div class="h-full transition-all duration-1000 {extendedDailyScore >= 80 ? 'bg-emerald-500' : extendedDailyScore >= 50 ? 'bg-violet-500' : 'bg-red-500'}" style="width: {extendedDailyScore}%"></div>
                </div>
                <p class="text-xs text-zinc-500 mt-3 font-mono">AVG OVER {range.toUpperCase()}</p>
            </div>
        </div>

        <!-- Session DNA -->
        <div class="lg:col-span-2 bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-6 flex flex-col">
            <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-4">Session DNA</h3>
            
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 flex-1">
                <!-- Clean Win -->
                {#if patterns['Clean Win']}
                    <div class="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-emerald-400">{patterns['Clean Win']}</span>
                        <span class="text-[10px] uppercase text-emerald-600/80 font-bold mt-2 tracking-wider">Clean Win</span>
                    </div>
                {/if}
                
                <!-- Overclocked -->
                {#if patterns['Overclocked']}
                    <div class="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-orange-400">{patterns['Overclocked']}</span>
                        <span class="text-[10px] uppercase text-orange-600/80 font-bold mt-2 tracking-wider">Overclocked</span>
                    </div>
                {/if}
                
                <!-- Grind -->
                {#if patterns['Grind']}
                    <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-blue-400">{patterns['Grind']}</span>
                        <span class="text-[10px] uppercase text-blue-600/80 font-bold mt-2 tracking-wider">Grind</span>
                    </div>
                {/if}
                
                <!-- Drift -->
                {#if patterns['Drift']}
                    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-red-400">{patterns['Drift']}</span>
                        <span class="text-[10px] uppercase text-red-600/80 font-bold mt-2 tracking-wider">Drift</span>
                    </div>
                {/if}
                
                <!-- Maintenance -->
                {#if patterns['Maintenance']}
                    <div class="bg-zinc-800/40 border border-zinc-700 rounded-lg p-4 flex flex-col items-center justify-center">
                        <span class="text-3xl font-bold text-zinc-400">{patterns['Maintenance']}</span>
                        <span class="text-[10px] uppercase text-zinc-600 font-bold mt-2 tracking-wider">Maintenance</span>
                    </div>
                {/if}
                
                {#if Object.values(patterns).reduce((a,b)=>a+b,0) === 0}
                    <div class="col-span-2 sm:col-span-5 flex items-center justify-center text-zinc-600 text-sm italic border border-dashed border-zinc-800 rounded-lg p-8">
                        No pattern data
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <!-- Input vs Output -->
    <div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-4 sm:p-6">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-6 gap-3">
            <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider">Input vs Output</h3>
            <div class="flex gap-4 text-[10px] font-mono uppercase flex-wrap">
                <div class="flex items-center gap-2"><div class="w-2 h-2 rounded-full bg-violet-500"></div><span class="text-violet-300">Sleep</span></div>
                <div class="flex items-center gap-2"><div class="w-2 h-2 rounded-sm bg-emerald-500/50 border border-emerald-500"></div><span class="text-emerald-300">Deep Work</span></div>
            </div>
        </div>
        <div class="h-64 w-full relative overflow-hidden">
            {#if sleepVsWork.length > 0}
                {@const maxSleep = Math.max(...sleepVsWork.map(d => d.sleep_minutes || 0), 600)}
                {@const maxDeep = Math.max(...sleepVsWork.map(d => d.deep_minutes || 0), 300)}
                
                <!-- Grid Lines -->
                <div class="absolute inset-0 flex flex-col justify-between text-[10px] text-zinc-700 font-mono pointer-events-none z-0">
                    <div class="border-b border-dashed border-zinc-800/50 w-full"></div>
                    <div class="border-b border-dashed border-zinc-800/50 w-full"></div>
                    <div class="border-b border-dashed border-zinc-800/50 w-full"></div>
                    <div class="border-b border-zinc-800 w-full"></div>
                </div>
                
                <!-- Chart -->
                <div class="absolute inset-0 flex items-end justify-between px-1 sm:px-2 z-10 gap-0.5 sm:gap-1">
                    {#each sleepVsWork as day, i}
                        <div class="flex-1 flex flex-col justify-end items-center h-full relative group min-w-0">
                            <!-- Deep Work Bar -->
                            <div class="w-full max-w-[16px] sm:max-w-[24px] bg-emerald-500/20 border-t border-x border-emerald-500/40 rounded-t-sm transition-all group-hover:bg-emerald-500/40" style="height: {scaleY(day.deep_minutes, maxDeep)}%"></div>
                            
                            <!-- Sleep Dot -->
                            {#if day.sleep_minutes}
                                <div class="absolute w-2 h-2 bg-violet-500 rounded-full border-2 border-zinc-900 shadow-sm z-20 transition-all group-hover:scale-125" style="bottom: {scaleY(day.sleep_minutes, maxSleep)}%; margin-bottom: -4px;"></div>
                            {/if}
                            
                            <!-- Tooltip -->
                            <div class="absolute bottom-full mb-2 hidden group-hover:block bg-zinc-800 border border-zinc-700 p-2 rounded text-[10px] font-mono whitespace-nowrap z-30 shadow-xl pointer-events-none">
                                <div class="text-zinc-400 mb-1">{day.date}</div>
                                <div class="text-violet-400">Sleep: {day.sleep_minutes || 0}m</div>
                                <div class="text-emerald-400">Deep: {day.deep_minutes || 0}m</div>
                            </div>
                            
                            <!-- Date Label -->
                            <div class="absolute -bottom-6 text-[10px] text-zinc-600 font-mono truncate w-full text-center">
                                {#if range === 'month' && i % 7 === 0}
                                    {getMonthName(day.date)}
                                {:else}
                                    {fmtDate(day.date)}
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
            {:else}
                <div class="flex items-center justify-center h-full text-zinc-600 text-sm italic">Insufficient data for correlation analysis.</div>
            {/if}
        </div>
    </div>

    <!-- Cognitive Chronotype - FIXED GRID -->
    <div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-4 sm:p-6">
        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-6">Cognitive Chronotype</h3>
        <div class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12 gap-1 sm:gap-2">
            {#each Array(24) as _, hour}
                <div class="flex flex-col gap-1 group">
                    <div class="h-10 sm:h-12 rounded-md flex items-center justify-center text-xs sm:text-sm font-bold {getHeatColor(chronotype[hour] || 0)} transition-all group-hover:scale-105 cursor-default border border-transparent px-1">
                        {(chronotype[hour] || 0).toFixed(1)}
                    </div>
                    <div class="text-[9px] sm:text-[10px] text-center text-zinc-600 font-mono group-hover:text-zinc-400">{hour.toString().padStart(2, '0')}</div>
                </div>
            {/each}
        </div>
        <p class="text-[10px] text-zinc-600 mt-4 text-right">Average Focus Quality per Hour</p>
    </div>

    <!-- Energy Ledger - FIXED RESPONSIVE LAYOUT -->
    <div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-4 sm:p-6">
        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-6">Energy Ledger (Net Profit/Loss)</h3>
        <div class="space-y-4 sm:space-y-6">
            {#each Object.entries(energyLedger) as [domain, val]}
                <div class="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4 group">
                    <div class="sm:w-32 text-sm font-medium text-zinc-400 group-hover:text-white transition-colors truncate">
                        {domain}
                    </div>
                    <div class="flex-1 h-8 relative flex items-center">
                        <div class="absolute left-1/2 w-px h-full bg-zinc-800"></div>
                        <div class="w-full h-2 bg-zinc-800/50 rounded-full overflow-hidden flex relative">
                            {#if val > 0}
                                <div class="absolute left-1/2 h-full transition-all duration-500 rounded-r-full" style={getLedgerStyle(val)}></div>
                            {:else}
                                <div class="absolute right-1/2 h-full transition-all duration-500 rounded-l-full" style={getLedgerStyle(val)}></div>
                            {/if}
                        </div>
                    </div>
                    <div class="sm:w-16 text-xs font-mono text-right {val > 0 ? 'text-emerald-500' : val < 0 ? 'text-red-500' : 'text-zinc-600'}">
                        {val > 0 ? '+' : ''}{val.toFixed(1)}
                    </div>
                </div>
            {/each}
            {#if Object.keys(energyLedger).length === 0}
                <div class="text-center text-zinc-600 text-sm italic py-8">No energy delta recorded yet.</div>
            {/if}
        </div>
    </div>
    
    <!-- Intake Statistics (NEW SECTION) -->
    <div class="bg-zinc-900/20 border border-zinc-800/50 rounded-xl p-4 sm:p-6">
        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-6">Intake Statistics</h3>
        {#if dailyIntakes.length > 0}
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div class="bg-zinc-800/30 p-4 rounded-lg">
                    <div class="text-3xl font-bold text-cyan-400">
                        {Math.round(dailyIntakes.reduce((sum, i) => sum + (i?.water_count || 0), 0) / dailyIntakes.length)}
                    </div>
                    <div class="text-[10px] text-zinc-400 uppercase mt-1 tracking-wider">Avg Water (glasses)</div>
                </div>
                <div class="bg-zinc-800/30 p-4 rounded-lg">
                    <div class="text-3xl font-bold text-cyan-400">
                        {Math.round(dailyIntakes.filter(i => i?.breakfast_time).length / dailyIntakes.length * 100)}%
                    </div>
                    <div class="text-[10px] text-zinc-400 uppercase mt-1 tracking-wider">Breakfast Consistency</div>
                </div>
                <div class="bg-zinc-800/30 p-4 rounded-lg">
                    <div class="text-3xl font-bold text-cyan-400">
                        {Math.round((dailyIntakes.filter(i => i?.water_count >= 8).length / dailyIntakes.length) * 100)}%
                    </div>
                    <div class="text-[10px] text-zinc-400 uppercase mt-1 tracking-wider">Hydration Days</div>
                </div>
            </div>
        {:else}
            <div class="text-center text-zinc-600 text-sm italic py-8">No intake data available</div>
        {/if}
    </div>
    
    {/if}
</div>
