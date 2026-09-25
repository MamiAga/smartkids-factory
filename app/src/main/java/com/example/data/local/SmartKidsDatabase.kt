package com.example.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface VoiceDao {
    @Query("SELECT * FROM voice_registry ORDER BY languageCode ASC")
    fun getAllVoices(): Flow<List<VoiceLicenseEntity>>

    @Query("SELECT * FROM voice_registry WHERE languageCode = :langCode LIMIT 1")
    suspend fun getVoiceByLanguage(langCode: String): VoiceLicenseEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVoices(voices: List<VoiceLicenseEntity>)

    @Update
    suspend fun updateVoice(voice: VoiceLicenseEntity)

    @Query("UPDATE voice_registry SET isApproved = :approved WHERE voiceId = :voiceId")
    suspend fun setApproval(voiceId: String, approved: Boolean)

    @Query("SELECT COUNT(*) FROM voice_registry WHERE isCommercialUseAllowed = 0 OR isApproved = 0")
    fun getUnapprovedOrBlockedCount(): Flow<Int>
}

@Dao
interface EpisodeDao {
    @Query("SELECT * FROM episode_dna ORDER BY createdAt DESC")
    fun getAllEpisodes(): Flow<List<EpisodeDnaEntity>>

    @Query("SELECT * FROM episode_dna WHERE episodeId = :id LIMIT 1")
    suspend fun getEpisodeById(id: String): EpisodeDnaEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEpisode(episode: EpisodeDnaEntity)

    @Update
    suspend fun updateEpisode(episode: EpisodeDnaEntity)

    @Delete
    suspend fun deleteEpisode(episode: EpisodeDnaEntity)
}

@Dao
interface PipelineDao {
    @Query("SELECT * FROM pipeline_jobs ORDER BY updatedAt DESC")
    fun getAllJobs(): Flow<List<PipelineJobEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertJob(job: PipelineJobEntity)

    @Update
    suspend fun updateJob(job: PipelineJobEntity)

    @Query("DELETE FROM pipeline_jobs WHERE jobId = :id")
    suspend fun deleteJob(id: String)

    // Supabase is the source of truth: the local table is replaced by the cloud list on every sync.
    @Query("DELETE FROM pipeline_jobs")
    suspend fun deleteAllJobs()

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertJobs(jobs: List<PipelineJobEntity>)
}

@Dao
interface ChatDao {
    @Query("SELECT * FROM chat_messages ORDER BY timestamp ASC")
    fun getAllMessages(): Flow<List<ChatMessageEntity>>

    @Insert
    suspend fun insertMessage(message: ChatMessageEntity)

    @Query("DELETE FROM chat_messages")
    suspend fun clearHistory()
}

@Dao
interface AutomationControlDao {
    @Query("SELECT * FROM automation_control WHERE id = 1 LIMIT 1")
    fun getControl(): Flow<AutomationControlEntity?>

    @Query("SELECT * FROM automation_control WHERE id = 1 LIMIT 1")
    suspend fun getControlSnapshot(): AutomationControlEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(control: AutomationControlEntity)

    @Query("UPDATE automation_control SET enabled = :enabled, updatedAt = :timestamp WHERE id = 1")
    suspend fun setEnabled(enabled: Boolean, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE automation_control SET dailyMasterEpisodes = :episodes, updatedAt = :timestamp WHERE id = 1")
    suspend fun setDailyTarget(episodes: Int, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE automation_control SET activeLanguagesJson = :languagesJson, updatedAt = :timestamp WHERE id = 1")
    suspend fun setActiveLanguages(languagesJson: String, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE automation_control SET scheduleTime = :scheduleTime, timezone = :timezone, updatedAt = :timestamp WHERE id = 1")
    suspend fun setSchedule(scheduleTime: String, timezone: String, timestamp: Long = System.currentTimeMillis())
}

@Dao
interface SystemEventDao {
    @Query("SELECT * FROM system_events ORDER BY timestamp DESC LIMIT 50")
    fun getRecentEvents(): Flow<List<SystemEventEntity>>

    @Insert
    suspend fun insertEvent(event: SystemEventEntity)
}

@Database(
    entities = [
        VoiceLicenseEntity::class,
        EpisodeDnaEntity::class,
        PipelineJobEntity::class,
        ChatMessageEntity::class,
        AutomationControlEntity::class,
        SystemEventEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class SmartKidsDatabase : RoomDatabase() {
    abstract fun voiceDao(): VoiceDao
    abstract fun episodeDao(): EpisodeDao
    abstract fun pipelineDao(): PipelineDao
    abstract fun chatDao(): ChatDao
    abstract fun automationControlDao(): AutomationControlDao
    abstract fun systemEventDao(): SystemEventDao

    companion object {
        @Volatile
        private var INSTANCE: SmartKidsDatabase? = null

        fun getDatabase(context: android.content.Context): SmartKidsDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    SmartKidsDatabase::class.java,
                    "smartkids_network.db"
                )
                .fallbackToDestructiveMigration(dropAllTables = true)
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
