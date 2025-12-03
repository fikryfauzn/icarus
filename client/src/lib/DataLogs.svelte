<script>
  import { onMount } from 'svelte';
  import { get } from './api';
  import StaticHorizon from './StaticHorizon.svelte';
  import MonthCalendar from './MonthCalendar.svelte';

  // State
  let calendarData = { performance: [], sleep: [] };
  let selectedDate = new Date().toISOString().split('T')[0];
  let activeContext = 'performance'; 
  
  // Inspector Data
  let dailySessions = [];
  let dailySleep = null;  // Sleep that ended today (yesterday's sleep)
  let tomorrowSleep = null; // Sleep that starts today (today's sleep)
  let dailyIntake = null;
  let loadingDetails = false;

  // Hover state for chart
  let hoveredItem = null;

  // Modal state
  let showDetailModal = false;
  let selectedSession = null;

  // Daily score
  let dailyScore = 0;
  let extendedDailyScore = 0;

  // --- Computed Daily Metrics ---
  $: deepWorkMinutes = dailySessions.filter(s => s.context.work_type === 'Deep').reduce((acc, s) => acc + (s.duration_minutes || 0), 0);
  $: totalWorkMinutes = dailySessions.reduce((acc, s) => acc + (s.duration_minutes || 0), 0);
  $: deepWorkRatio = totalWorkMinutes ? Math.round((deepWorkMinutes / totalWorkMinutes) * 100) : 0;
  
  // Intake calculations
  $: intakePoints = calculateIntakePoints(dailyIntake);
  $: extendedDailyScore = Math.min(100, dailyScore + intakePoints);
  
  // Calculate average focus quality for score
  $: avgFocusQuality = (() => {
    const sessionsWithOutcome = dailySessions.filter(s => s.outcome);
    return sessionsWithOutcome.length > 0 
      ? sessionsWithOutcome.reduce((acc, s) => acc + s.outcome.focus_quality, 0) / sessionsWithOutcome.length
      : 0;
  })();

  // Get tomorrow's date for sleep fetch
  function getTomorrowDate(date) {
    const tomorrow = new Date(date);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  }

  onMount(async () => {
    try {
        calendarData = await get('/analytics/calendar');
        loadDayDetails(selectedDate);
    } catch (e) { console.error(e); }
  });

  async function loadDayDetails(date) {
      if (!date) return;
      selectedDate = date;
      loadingDetails = true;
      try {
          const tomorrowDate = getTomorrowDate(date);
          const [sess, slp, tomorrowSlp, scoreData, intakeData] = await Promise.all([
              get(`/sessions?start_date=${date}&end_date=${date}`),
              get(`/sleep?date=${date}`),
              get(`/sleep?date=${tomorrowDate}`),
              get(`/analytics/score?start=${date}&end=${date}`),
              get(`/intake?date=${date}`)
          ]);
          dailySessions = sess.sort((a,b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
          dailySleep = slp;
          tomorrowSleep = tomorrowSlp;
          dailyIntake = intakeData;
          dailyScore = scoreData.score || calculateFallbackScore(sess, slp);
      } catch(e) { 
          console.error(e);
          // Fallback calculation if API fails
          dailyScore = calculateFallbackScore(dailySessions, dailySleep);
      }
      finally { loadingDetails = false; }
  }

  function calculateFallbackScore(sessions, sleep) {
      if (!sessions.length && !sleep) return 0;
      let score = 0;
      
      // Output (60pts): 1 point per 5 mins deep work
      const deepMins = sessions.filter(s => s.context.work_type === 'Deep').reduce((acc,s) => acc + (s.duration_minutes||0), 0);
      score += Math.min(60, Math.floor(deepMins / 5));
      
      // Input (20pts): Sleep
      if (sleep) {
          if (sleep.duration_minutes >= 420) score += 10;
          else if (sleep.duration_minutes >= 360) score += 5;
          if (sleep.sleep_quality >= 4) score += 10;
      }
      
      // Efficiency (20pts): Avg Focus × 4
      const sessionsWithOutcome = sessions.filter(s => s.outcome);
      if (sessionsWithOutcome.length > 0) {
          const avgFocus = sessionsWithOutcome.reduce((acc, s) => acc + s.outcome.focus_quality, 0) / sessionsWithOutcome.length;
          score += Math.floor(avgFocus * 4);
      }
      
      return Math.min(100, score);
  }

  // Intake point calculation
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

  // Helper functions for chart
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

  function getSleepPosition(sleepData, isTomorrowSleep = false) {
    if (!sleepData) return null;
    
    const start = new Date(sleepData.sleep_start);
    const end = new Date(sleepData.sleep_end);
    const chartDate = new Date(selectedDate);
    
    // For tomorrow's sleep, we only show the part that's in today (if it starts today)
    if (isTomorrowSleep) {
      // If sleep starts tomorrow, don't show on today's chart
      if (start.getDate() !== chartDate.getDate()) return null;
      // Only show from start time to 24:00 (end of today)
      const endOfToday = new Date(chartDate);
      endOfToday.setHours(24, 0, 0, 0);
      
      const sleepEnd = end < endOfToday ? end : endOfToday;
      const startMins = (start.getHours() * 60) + start.getMinutes();
      const dur = (sleepEnd - start) / 1000 / 60;
      
      if (dur <= 0) return null;
      
      return { 
        left: `${(startMins / 1440) * 100}%`, 
        width: `${(dur / 1440) * 100}%`,
        isPartial: end > endOfToday
      };
    } else {
      // For today's sleep (yesterday's sleep), we only show the part that's in today
      // If sleep ended before today started, don't show
      const startOfToday = new Date(chartDate);
      startOfToday.setHours(0, 0, 0, 0);
      
      if (end <= startOfToday) return null;
      
      // Show from 00:00 to end time (or to sleep end if before end of day)
      const sleepStart = start < startOfToday ? startOfToday : start;
      const endMins = (end.getHours() * 60) + end.getMinutes();
      const startMins = sleepStart.getHours() * 60 + sleepStart.getMinutes();
      const dur = (end - sleepStart) / 1000 / 60;
      
      if (dur <= 0) return null;
      
      return { 
        left: `${(startMins / 1440) * 100}%`, 
        width: `${(dur / 1440) * 100}%`,
        isPartial: start < startOfToday
      };
    }
  }

  function formatTime(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  function getEndTime(session) {
    const start = new Date(session.start_time);
    const duration = session.duration_minutes || 0;
    const end = new Date(start.getTime() + duration * 60000);
    return end.toISOString();
  }

  // Modal functions
  function openDetail(session) {
    selectedSession = session;
    showDetailModal = true;
  }

  async function handleDelete(id) {
    if(!confirm("Permanently delete this record?")) return;
    await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
    showDetailModal = false;
    selectedSession = null;
    loadDayDetails(selectedDate);
  }

  // Domain minutes calculation
  function getDomainMinutes(sessions) {
      const domainMap = {};
      sessions.forEach(s => {
          const domain = s.context.domain;
          const mins = s.duration_minutes || 0;
          domainMap[domain] = (domainMap[domain] || 0) + mins;
      });
      return Object.entries(domainMap)
          .map(([name, minutes]) => ({ name, minutes }))
          .sort((a, b) => b.minutes - a.minutes);
  }
</script>

<div class="h-full w-full p-6">
    <div class="grid grid-cols-12 gap-8 h-full">
        
        <div class="col-span-12 lg:col-span-8 flex flex-col gap-8 h-full">
            
            <!-- Chart Container -->
            <div class="flex-1 min-h-0 bg-[#0c0c0e] border border-zinc-800 rounded-xl p-0 relative overflow-hidden flex flex-col shadow-inner group/chart">
                
                <div class="absolute top-4 left-6 right-6 flex justify-between items-start z-20 pointer-events-none">
                    <div class="flex flex-col">
                        <h3 class="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">Temporal Horizon</h3>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="text-[9px] text-zinc-600 font-mono">Top: Output</span>
                            <span class="text-[9px] text-zinc-700 font-mono">|</span>
                            <span class="text-[9px] text-zinc-600 font-mono">Bottom: Bio-Cost & Sleep</span>
                        </div>
                    </div>

                    <!-- Hover Tooltip -->
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
                                        <span class="text-xs font-mono text-zinc-300">{formatTime(s.start_time)} – {formatTime(getEndTime(s))}</span>
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
                                        <span class="text-[9px] text-zinc-500 uppercase font-bold">{sl.label || 'Sleep'}</span>
                                        <span class="text-xs font-bold text-violet-300">Sleep Protocol</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[9px] text-zinc-500 uppercase font-bold">Time</span>
                                        <span class="text-xs font-mono text-zinc-300">{formatTime(sl.sleep_start)} – {formatTime(sl.sleep_end)}</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[9px] text-zinc-500 uppercase font-bold">Quality</span>
                                        <span class="text-xs font-mono text-white">{sl.sleep_quality}/5</span>
                                    </div>
                                {/if}
                            </div>
                        {:else}
                            <!-- Extended Daily Score Display -->
                            <div class="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800/50 px-4 py-1.5 rounded-full flex gap-3 mt-4">
                                <span class="text-[10px] text-zinc-500 font-bold uppercase tracking-wider pt-0.5">Daily Index</span>
                                <span class="text-sm font-mono font-bold {extendedDailyScore >= 80 ? 'text-emerald-400' : extendedDailyScore >= 50 ? 'text-violet-400' : 'text-red-400'}">
                                    {extendedDailyScore}
                                </span>
                                {#if intakePoints > 0}
                                    <span class="text-[9px] text-cyan-400 font-bold" title="Includes intake points">+{intakePoints} intake</span>
                                {/if}
                            </div>
                        {/if}
                    </div>

                    <div class="pointer-events-auto flex gap-2">
                        <button on:click={() => loadDayDetails(new Date().toISOString().split('T')[0])} class="bg-zinc-800/50 text-zinc-400 border border-zinc-700/50 px-3 py-1.5 rounded text-[10px] uppercase font-bold hover:bg-zinc-700 hover:text-white transition-all backdrop-blur-md">
                            Today
                        </button>
                    </div>
                </div>

                <!-- Chart Area -->
                <div class="relative flex-1 w-full mt-4">
                    <div class="absolute top-[70%] left-0 right-0 h-px bg-zinc-700 z-10"></div>
                    
                    <div class="absolute inset-0 pointer-events-none">
                        {#each [0, 4, 8, 12, 16, 20, 24] as hour}
                            {@const position = (hour / 24) * 100}
                            <div
                                class="absolute top-0 bottom-0 border-r border-zinc-800/30"
                                style="left: {position}%;"
                            >
                                <span class="absolute bottom-2 -right-3 text-[9px] text-zinc-700 font-mono">{hour.toString().padStart(2, '0')}:00</span>
                            </div>
                        {/each}
                    </div>

                    <div class="absolute inset-0 mx-[2px]"> 
                        <!-- Yesterday's sleep that ended today -->
                        {#if dailySleep}
                            {@const pos = getSleepPosition(dailySleep, false)}
                            {#if pos}
                                <div 
                                    class="absolute top-[70%] bottom-0 z-0 bg-violet-500/15 border-x border-violet-500/30 hover:bg-violet-500/25 transition-colors cursor-crosshair"
                                    style="left: {pos.left}; width: {pos.width};"
                                    on:mouseenter={() => hoveredItem = { type: 'sleep', data: { ...dailySleep, label: 'Previous Night' } }}
                                    on:mouseleave={() => hoveredItem = null}
                                >
                                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-violet-500/70"></div>
                                    {#if pos.isPartial}
                                        <div class="absolute left-0 top-0 bottom-0 w-1 bg-violet-400/50"></div>
                                    {/if}
                                </div>
                            {/if}
                        {/if}

                        <!-- Today's sleep that extends to tomorrow -->
                        {#if tomorrowSleep}
                            {@const pos = getSleepPosition(tomorrowSleep, true)}
                            {#if pos}
                                <div 
                                    class="absolute top-[70%] bottom-0 z-0 bg-indigo-500/15 border-x border-indigo-500/30 hover:bg-indigo-500/25 transition-colors cursor-crosshair"
                                    style="left: {pos.left}; width: {pos.width};"
                                    on:mouseenter={() => hoveredItem = { type: 'sleep', data: { ...tomorrowSleep, label: 'Current Night' } }}
                                    on:mouseleave={() => hoveredItem = null}
                                >
                                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-indigo-500/70"></div>
                                    {#if pos.isPartial}
                                        <div class="absolute right-0 top-0 bottom-0 w-1 bg-indigo-400/50"></div>
                                    {/if}
                                </div>
                            {/if}
                        {/if}

                        {#each dailySessions as s}
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
                                style="left: {pos.left}; width: {pos.width}; height: {s.outcome ? (score * 0.5) : 30}%;"
                                on:mouseenter={() => hoveredItem = { type: 'session', data: s }}
                                on:mouseleave={() => hoveredItem = null}
                                on:click={() => openDetail(s)}
                            >
                                <div class="w-full h-full rounded-t-[2px] {color} {opacity} border-t border-x border-white/10 bg-gradient-to-b from-white/10 to-transparent backdrop-blur-[1px] hover:brightness-125 shadow-[0_-4px_15px_rgba(0,0,0,0.3)] {hoveredItem?.type === 'session' && hoveredItem.data?.id === s.id ? 'brightness-125 ring-1 ring-white/30' : ''}"></div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>

            <!-- Three Boxes Below (same as before, keep the intake section) -->
            <div class="h-72 flex-none grid grid-cols-3 gap-8">
                <!-- Performance Box -->
                <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-5 relative overflow-hidden flex flex-col">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mt-1">
                            Performance
                        </h3>
                    </div>

                    <div class="flex items-end gap-2 mb-4">
                        <span class="text-4xl font-light text-white">{deepWorkMinutes}</span>
                        <span class="text-sm text-zinc-500 mb-1">deep minutes</span>
                    </div>
                    <div class="space-y-1.5 overflow-y-auto max-h-[100px] pr-2 scrollbar-thin scrollbar-thumb-zinc-800">
                        {#if dailySessions.length > 0}
                            {#each getDomainMinutes(dailySessions) as domain}
                                <div class="flex items-center gap-2 text-xs">
                                    <div class="w-2 h-2 rounded-full {domainColors[domain.name] || 'bg-zinc-500'}"></div>
                                    <span class="text-zinc-400 flex-1 truncate">{domain.name}</span>
                                    <span class="font-mono text-zinc-500">{domain.minutes}m</span>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </div>
                
                <!-- Deep Work Box -->
                <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-5 relative overflow-hidden flex flex-col">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mt-1">
                            Deep Work
                        </h3>
                    </div>

                    <div class="text-white mb-4">
                        <span class="text-4xl font-mono font-light">{Math.floor(deepWorkMinutes/60)}</span>
                        <span class="text-lg text-zinc-500">h</span>
                        <span class="text-4xl font-mono font-light">{deepWorkMinutes%60}</span>
                        <span class="text-lg text-zinc-500">m</span>
                    </div>
                    <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-2">
                        <div class="bg-emerald-500 h-full" style="width: {deepWorkRatio}%"></div>
                    </div>
                    <div class="mt-4 text-[10px] text-zinc-500 uppercase tracking-wider">
                        {deepWorkRatio}% of total work
                    </div>
                </div>

                <!-- Bio-Input Box with intake -->
                <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-5 relative overflow-hidden flex flex-col">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mt-1">
                            Bio-Input
                        </h3>
                        {#if intakePoints > 0}
                            <span class="text-[10px] font-mono text-cyan-400">+{intakePoints} pts</span>
                        {/if}
                    </div>

                    {#if dailySleep}
                        <div class="mb-4">
                            <div class="text-3xl font-bold text-violet-300 mb-1">{dailySleep.sleep_quality}/5</div>
                            <div class="text-[10px] text-zinc-400">Sleep Quality</div>
                        </div>
                        <div class="text-[10px] text-zinc-500 mb-2">
                            Duration: {Math.floor((dailySleep.duration_minutes || 0) / 60)}h {(dailySleep.duration_minutes || 0) % 60}m
                        </div>
                    {:else}
                        <div class="text-zinc-600 text-xs italic mb-4">No Sleep Data</div>
                    {/if}

                    {#if dailyIntake}
                        <div class="mt-4 pt-4 border-t border-zinc-800/50">
                            <div class="text-[10px] text-zinc-500 uppercase font-bold mb-2">Intake</div>
                            <div class="text-[10px] text-zinc-400 space-y-1">
                                <div class="flex justify-between">
                                    <span>Water:</span>
                                    <span class="font-mono {dailyIntake.water_count >= 8 ? 'text-cyan-400' : 'text-zinc-600'}">{dailyIntake.water_count} glasses</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Meals:</span>
                                    <span class="font-mono">
                                        {#if dailyIntake.breakfast_time}B{/if}
                                        {#if dailyIntake.lunch_time} L{/if}
                                        {#if dailyIntake.dinner_time} D{/if}
                                        {#if !dailyIntake.breakfast_time && !dailyIntake.lunch_time && !dailyIntake.dinner_time}None{/if}
                                    </span>
                                </div>
                            </div>
                        </div>
                    {:else}
                        <div class="mt-4 pt-4 border-t border-zinc-800/50 text-zinc-600 text-xs italic">
                            No Intake Data
                        </div>
                    {/if}
                </div>
            </div>
        </div>

        <!-- Right Column -->
        <div class="col-span-12 lg:col-span-4 h-full min-h-0">
            <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-xl h-full flex flex-col relative overflow-hidden">
                
                <!-- Top: Mode Selector -->
                <div class="p-4 border-b border-zinc-800/50 bg-zinc-900/20 flex-none flex justify-between items-center">
                    <div class="flex bg-black p-0.5 rounded-lg border border-zinc-800">
                        <button 
                            on:click={() => activeContext = 'performance'}
                            class="px-3 py-1 text-[10px] uppercase font-bold rounded-md transition-all {activeContext === 'performance' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-600 hover:text-zinc-400'}"
                        >
                            Performance
                        </button>
                        <button 
                            on:click={() => activeContext = 'sleep'}
                            class="px-3 py-1 text-[10px] uppercase font-bold rounded-md transition-all {activeContext === 'sleep' ? 'bg-zinc-800 text-white shadow' : 'text-zinc-600 hover:text-zinc-400'}"
                        >
                            Sleep
                        </button>
                    </div>

                    <span class="text-[10px] font-mono text-zinc-600">{dailySessions.length} SESSIONS</span>
                </div>

                <!-- Scrollable Content Area -->
                <div class="flex-1 overflow-y-auto p-0 scrollbar-thin scrollbar-thumb-zinc-800">
                    <!-- Calendar -->
                    <div class="p-4 border-b border-zinc-800/50">
                        <MonthCalendar 
                            data={activeContext === 'performance' ? calendarData.performance : calendarData.sleep} 
                            type={activeContext}
                            {selectedDate}
                            on:select={(e) => loadDayDetails(e.detail)}
                        />
                    </div>
                    
                    <!-- Flight Log -->
                    <div class="h-[calc(100%-280px)] min-h-0 flex flex-col">
                        <div class="p-4 border-b border-zinc-800/50 bg-zinc-900/20 text-xs font-bold text-zinc-500 uppercase tracking-wider flex-none">
                            Flight Log
                        </div>
                        <div class="flex-1 overflow-y-auto p-0 scrollbar-thin scrollbar-thumb-zinc-800">
                            {#if dailySessions.length === 0}
                                <div class="p-8 text-center text-zinc-700 text-xs italic">No activity recorded.</div>
                            {:else}
                                <div class="divide-y divide-zinc-800/30">
                                    {#each dailySessions as s}
                                        <div 
                                            class="p-4 hover:bg-zinc-800/20 transition-colors group cursor-pointer"
                                            on:mouseenter={() => hoveredItem = { type: 'session', data: s }}
                                            on:mouseleave={() => hoveredItem = null}
                                            on:click={() => openDetail(s)}
                                        >
                                            <div class="flex justify-between items-start mb-1">
                                                <span class="font-mono text-[10px] text-zinc-500">{formatTime(s.start_time)}</span>
                                                {#if s.outcome}
                                                    <div class="flex gap-1">
                                                        {#if s.context.work_type === 'Deep'}
                                                            <span class="text-[9px] px-1.5 py-0.5 bg-emerald-950 border border-emerald-900 text-emerald-400 rounded">D</span>
                                                        {/if}
                                                        <span class="text-[9px] px-1.5 py-0.5 bg-zinc-950 border border-zinc-800 rounded text-zinc-400">
                                                            R:{s.outcome.progress_rating}
                                                        </span>
                                                    </div>
                                                {/if}
                                            </div>
                                            <div class="text-sm font-bold text-zinc-300 mb-0.5">{s.context.project_name}</div>
                                            <div class="text-[10px] text-zinc-500 truncate">{s.context.activity_description}</div>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Session Detail Modal (FIXED: Now includes full content) -->
{#if showDetailModal && selectedSession}
    <div class="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-xl w-full max-w-2xl shadow-2xl relative">
            <div class="flex justify-between items-start mb-6 border-b border-zinc-800 pb-4">
                <div>
                    <h3 class="text-xl font-bold text-white tracking-tight">{selectedSession.context.project_name}</h3>
                    <div class="flex gap-2 mt-2">
                        <span class="text-xs font-mono bg-zinc-800 px-2 py-1 rounded text-zinc-400 border border-zinc-700">{selectedSession.context.domain}</span>
                        <span class="text-xs font-mono bg-zinc-800 px-2 py-1 rounded text-zinc-400 border border-zinc-700">{selectedSession.context.work_type}</span>
                    </div>
                </div>
                <button on:click={() => showDetailModal = false} class="text-zinc-500 hover:text-white">✕</button>
            </div>
            <div class="space-y-8">
                <div class="grid grid-cols-2 gap-8">
                    <div class="space-y-2">
                         <h4 class="text-xs uppercase font-bold text-zinc-500 tracking-wider mb-2">Entry State</h4>
                         <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                            <span class="text-xs text-zinc-400">Energy</span>
                            <div class="flex gap-1">
                                {#each Array(10) as _, i}
                                    <div class="w-1 h-3 rounded-full {i < selectedSession.before.energy ? 'bg-emerald-500' : 'bg-zinc-800'}"></div>
                                {/each}
                            </div>
                         </div>
                         <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                            <span class="text-xs text-zinc-400">Stress</span>
                            <div class="flex gap-1">
                                {#each Array(10) as _, i}
                                    <div class="w-1 h-3 rounded-full {i < selectedSession.before.stress ? 'bg-rose-500' : 'bg-zinc-800'}"></div>
                                {/each}
                            </div>
                         </div>
                    </div>
                    <div class="space-y-2">
                         <h4 class="text-xs uppercase font-bold text-zinc-500 tracking-wider mb-2">Exit State</h4>
                         {#if selectedSession.outcome}
                             <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                                <span class="text-xs text-zinc-400">Energy</span>
                                <div class="flex gap-1">
                                    {#each Array(10) as _, i}
                                        <div class="w-1 h-3 rounded-full {i < selectedSession.after.energy ? 'bg-emerald-500' : 'bg-zinc-800'}"></div>
                                    {/each}
                                </div>
                             </div>
                             <div class="flex justify-between items-center bg-zinc-950/50 p-3 rounded border border-zinc-800">
                                <span class="text-xs text-zinc-400">Stress</span>
                                <div class="flex gap-1">
                                    {#each Array(10) as _, i}
                                        <div class="w-1 h-3 rounded-full {i < selectedSession.after.stress ? 'bg-rose-500' : 'bg-zinc-800'}"></div>
                                    {/each}
                                </div>
                             </div>
                         {:else}
                            <div class="h-full flex items-center justify-center text-xs text-zinc-600 italic border border-dashed border-zinc-800 rounded">
                                Session In Progress
                            </div>
                         {/if}
                    </div>
                </div>
                {#if selectedSession.outcome}
                    <div class="bg-zinc-950 p-5 rounded-lg border border-zinc-800 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full {selectedSession.outcome.completion_status === 'Completed' ? 'bg-emerald-500' : 'bg-amber-500'}"></div>
                        <div class="grid grid-cols-3 gap-4 text-center mb-4">
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Progress</div><div class="text-emerald-400 font-mono text-xl">{selectedSession.outcome.progress_rating}/5</div></div>
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Focus</div><div class="text-blue-400 font-mono text-xl">{selectedSession.outcome.focus_quality}/5</div></div>
                            <div><div class="text-zinc-500 text-[10px] uppercase font-bold">Quality</div><div class="text-violet-400 font-mono text-xl">{selectedSession.outcome.quality_rating}/5</div></div>
                        </div>
                        <div class="text-sm text-zinc-300 font-mono whitespace-pre-wrap bg-black/30 p-3 rounded border border-zinc-800/50">{selectedSession.outcome.evidence_note || "No evidence recorded."}</div>
                        
                        <div class="flex gap-4 mt-4 pt-4 border-t border-zinc-800/50">
                             <div class="text-xs text-zinc-500">Feeling: <span class="text-white font-bold uppercase">{selectedSession.after?.feel_tag}</span></div>
                             <div class="text-xs text-zinc-500">Duration: <span class="text-white font-mono">{selectedSession.duration_minutes}m</span></div>
                        </div>
                    </div>
                {/if}
            </div>
            <div class="mt-8 pt-4 border-t border-zinc-800 flex justify-between items-center">
                <button on:click={() => handleDelete(selectedSession.id)} class="text-red-500 hover:text-red-400 text-xs font-bold uppercase tracking-wider transition-colors">Delete Record</button>
                <button on:click={() => showDetailModal = false} class="bg-white text-black px-6 py-2 rounded font-bold hover:bg-zinc-200 transition-colors">Close</button>
            </div>
        </div>
    </div>
{/if}
