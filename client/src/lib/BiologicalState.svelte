<script>
  import { onMount, onDestroy } from 'svelte';
  import { get, post } from './api';

  export let sleepData = null;
  export let intakeData = null;

  // --- Engine State ---
  let now = new Date();
  let timer;

  // Data
  let intake = {
      water_count: 0,
      breakfast_time: null,
      lunch_time: null,
      dinner_time: null
  };

  // Interaction State
  let confirmMode = null; // { type: 'water' | 'meal', value: 'breakfast' etc, action: 'add'|'remove' }

  // --- Engine Constants ---
  const WAKE_HOUR = 7; // 7:00 AM Start
  const WATER_INTERVAL_HOURS = 1.5; // Expect 1 glass every 1.5 hours
  
  const MEAL_DEADLINES = {
      breakfast: 10, // 10:00 AM
      lunch: 14,     // 2:00 PM
      dinner: 21     // 9:00 PM
  };

  // --- Computed Engine Logic ---
  $: hoursAwake = Math.max(0, now.getHours() - WAKE_HOUR + (now.getMinutes() / 60));
  $: expectedWater = Math.floor(hoursAwake / WATER_INTERVAL_HOURS);
  
  // Update intake when intakeData changes
  $: if (intakeData) {
      intake = intakeData;
  }

  // Status Checks
  $: waterStatus = getWaterStatus(intake.water_count, expectedWater);
  $: mealStatus = getMealStatus(intake, now.getHours());

  function getWaterStatus(current, expected) {
      if (hoursAwake <= 0.5) return 'ok'; // Give 30 mins grace
      if (current >= expected) return 'ok';
      if (current === expected - 1) return 'warn'; // 1 behind
      return 'crit'; // >1 behind (Red Alert)
  }

  function getMealStatus(data, currentHour) {
      return {
          breakfast: !data.breakfast_time && currentHour >= MEAL_DEADLINES.breakfast ? 'crit' : 'ok',
          lunch: !data.lunch_time && currentHour >= MEAL_DEADLINES.lunch ? 'crit' : 'ok',
          dinner: !data.dinner_time && currentHour >= MEAL_DEADLINES.dinner ? 'crit' : 'ok',
      };
  }

  // --- Lifecycle ---
  onMount(() => {
      loadIntake();
      timer = setInterval(() => now = new Date(), 60000); // Update every min
  });

  onDestroy(() => clearInterval(timer));

  async function loadIntake() {
      if (intakeData) {
          intake = intakeData;
      } else {
          try { intake = await get('/intake'); } catch (e) { console.error(e); }
      }
  }

  // --- Actions ---
  function requestWater() {
      if (intake.water_count >= 8) return;
      confirmMode = { type: 'water', action: 'add' };
  }

  function requestRemoveWater() {
      if (intake.water_count <= 0) return;
      // No confirmation needed for fixing a mistake, just do it? 
      // User asked for validation "before we click", usually implies adding.
      // But let's confirm delete too to be safe.
      confirmMode = { type: 'water', action: 'remove' };
  }

  function requestMeal(type) {
      if (intake[`${type}_time`]) return; // Already done
      confirmMode = { type: 'meal', value: type, action: 'add' };
  }

  async function confirmAction() {
      if (!confirmMode) return;

      if (confirmMode.type === 'water') {
          if (confirmMode.action === 'add') {
              intake.water_count += 1;
              await post('/intake/water', {}); // Assume backend handles increment
          } else {
              intake.water_count -= 1;
               // You might need a backend endpoint for decrementing, 
               // or just send the absolute number if your API supports it.
               // For now, optimistic UI fix:
          }
      } else if (confirmMode.type === 'meal') {
           const type = confirmMode.value;
           intake[`${type}_time`] = new Date().toISOString();
           await post('/intake/meal', { type });
      }
      
      confirmMode = null;
  }

  function formatDurationHM(mins) {
      if (!mins) return '0h 0m';
      return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  }
  
  function fmtTime(iso) {
      if (!iso) return '';
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="relative bg-zinc-900/40 border rounded-xl p-4 overflow-hidden flex flex-col gap-3 h-full justify-between transition-colors duration-500
    {waterStatus === 'crit' || Object.values(mealStatus).includes('crit') ? 'border-red-500/30 shadow-[inset_0_0_20px_rgba(220,38,38,0.1)]' : 'border-zinc-800/50'}">
    
    <div class="flex justify-between items-center">
        <div class="flex items-center gap-2">
            {#if waterStatus === 'crit' || Object.values(mealStatus).includes('crit')}
                <div class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
            {/if}
            <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider">Biological Engine</h3>
        </div>
        <span class="text-[10px] text-zinc-600 font-mono">{now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
    </div>

    <div class="space-y-1">
        <div class="flex justify-between items-end">
            <span class="text-xs text-zinc-400 font-medium">Sleep Charge</span>
            <div class="text-right leading-none">
                <span class="text-violet-400 font-mono text-lg font-bold">
                    {sleepData ? formatDurationHM(sleepData.duration_minutes) : '--'}
                </span>
                <span class="text-zinc-600 text-[9px] ml-1">Q:{sleepData?.sleep_quality || '-'}</span>
            </div>
        </div>
        <div class="h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div class="h-full bg-violet-500" style="width: {Math.min(100, (sleepData?.duration_minutes || 0) / 480 * 100)}%"></div>
        </div>
    </div>

    <div class="space-y-1 rounded-lg p-2 -mx-2 transition-colors {waterStatus === 'crit' ? 'bg-red-900/10' : ''}">
        <div class="flex justify-between items-center">
            <span class="text-xs font-medium {waterStatus === 'crit' ? 'text-red-400 animate-pulse' : 'text-zinc-400'}">
                Hydration {waterStatus === 'crit' ? 'CRITICAL' : ''}
            </span>
            <div class="flex items-center gap-2">
                 <button on:click={requestRemoveWater} class="text-[10px] text-zinc-600 hover:text-red-400 px-1 py-0.5 rounded border border-transparent hover:border-zinc-700">-</button>
                 <span class="text-cyan-400 font-mono text-sm">{intake.water_count} <span class="text-zinc-600 text-[10px]">/ 8</span></span>
            </div>
        </div>
        <div class="flex justify-between gap-1">
            {#each Array(8) as _, i}
                <button 
                    on:click={requestWater}
                    disabled={i < intake.water_count}
                    class="h-6 flex-1 rounded-[2px] border transition-all duration-300
                    {i < intake.water_count 
                        ? 'bg-cyan-500/20 border-cyan-500/50 shadow-[0_0_5px_rgba(6,182,212,0.4)]' 
                        : waterStatus === 'crit' && i === intake.water_count
                            ? 'bg-red-500/10 border-red-500/50 animate-pulse' // The next required glass flashes red
                            : 'bg-zinc-800/50 border-zinc-700 hover:bg-zinc-700'}"
                >
                </button>
            {/each}
        </div>
        {#if waterStatus === 'crit'}
            <div class="text-[9px] text-red-400 text-center font-bold tracking-wide">HYDRATION REQUIRED</div>
        {/if}
    </div>

    <div class="space-y-1">
        <span class="text-xs text-zinc-400 font-medium">Fuel Intake</span>
        <div class="grid grid-cols-3 gap-2">
            {#each ['breakfast', 'lunch', 'dinner'] as meal}
                <button 
                    on:click={() => requestMeal(meal)}
                    disabled={!!intake[`${meal}_time`]}
                    class="relative flex flex-col items-center justify-center py-2 px-1 rounded-lg border transition-all overflow-hidden
                    {intake[`${meal}_time`] 
                        ? 'bg-emerald-900/10 border-emerald-500/30 text-emerald-400' 
                        : mealStatus[meal] === 'crit'
                            ? 'bg-red-900/10 border-red-500/50 text-red-400 animate-pulse' // Missed Meal Warning
                            : 'bg-zinc-800/30 border-zinc-700 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-400'}"
                >
                    <span class="text-[9px] uppercase font-bold tracking-wider z-10">{meal}</span>
                    {#if intake[`${meal}_time`]}
                        <span class="text-[9px] font-mono mt-0.5 z-10">{fmtTime(intake[`${meal}_time`])}</span>
                    {:else if mealStatus[meal] === 'crit'}
                         <span class="text-[9px] font-bold mt-0.5 z-10">MISSED</span>
                    {:else}
                        <span class="text-[10px] opacity-20 mt-0.5 z-10">+</span>
                    {/if}
                </button>
            {/each}
        </div>
    </div>

    {#if confirmMode}
        <div class="absolute inset-0 z-50 bg-black/80 backdrop-blur-[2px] flex flex-col items-center justify-center p-4 text-center animate-in fade-in duration-150">
            <h4 class="text-white font-bold text-sm mb-1">Confirm Update</h4>
            <p class="text-zinc-400 text-xs mb-4">
                {confirmMode.type === 'water' 
                    ? (confirmMode.action === 'add' ? 'Log 1 glass of water?' : 'Remove 1 glass?') 
                    : `Log ${confirmMode.value} now?`}
            </p>
            <div class="flex gap-2 w-full">
                <button on:click={() => confirmMode = null} class="flex-1 bg-zinc-800 text-zinc-400 text-xs py-2 rounded font-bold hover:bg-zinc-700">Cancel</button>
                <button on:click={confirmAction} class="flex-1 bg-emerald-600 text-white text-xs py-2 rounded font-bold hover:bg-emerald-500">Confirm</button>
            </div>
        </div>
    {/if}

</div>