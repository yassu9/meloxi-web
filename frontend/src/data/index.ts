import type { Album, Artist, Genre, LyricLine, Mood, Playlist, Track } from "@/types/music";

/* Real Spotify / Global Seed Data & Curated Top Hits */

export const artists: Artist[] = [
  { id: "a1", name: "Arijit Singh", image: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80", banner: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=1200&q=80", bio: "India's #1 Spotify Artist with over 100 Million Followers.", monthlyListeners: 105_000_000, genres: ["Bollywood", "Romantic", "Pop"] },
  { id: "a2", name: "The Weeknd", image: "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=500&q=80", banner: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1200&q=80", bio: "Global R&B & Synth-Pop Icon.", monthlyListeners: 112_000_000, genres: ["R&B", "Synth-Pop"] },
  { id: "a3", name: "Taylor Swift", image: "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=500&q=80", banner: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1200&q=80", bio: "Global Pop Superstar & Record Breaker.", monthlyListeners: 108_000_000, genres: ["Pop", "Folk"] },
  { id: "a4", name: "Pritam", image: "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=500&q=80", banner: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=1200&q=80", bio: "Mastermind Composer behind Bollywood's biggest chartbusters.", monthlyListeners: 48_000_000, genres: ["Bollywood", "Filmi"] },
  { id: "a5", name: "Dua Lipa", image: "https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?w=500&q=80", banner: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1200&q=80", bio: "Queen of Future Nostalgia & Dance Pop.", monthlyListeners: 75_000_000, genres: ["Dance Pop", "Disco"] },
  { id: "a6", name: "Shreya Ghoshal", image: "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=500&q=80", banner: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=1200&q=80", bio: "Nightingale of India.", monthlyListeners: 39_000_000, genres: ["Melody", "Classical Pop"] },
  { id: "a7", name: "Lofi Girl", image: "https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=500&q=80", banner: "https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=1200&q=80", bio: "Beats to relax & study to.", monthlyListeners: 22_000_000, genres: ["Lo-Fi", "Chillhop"] },
  { id: "a8", name: "Coldplay", image: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=500&q=80", banner: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=1200&q=80", bio: "Legendary Stadium Rock & Pop Band.", monthlyListeners: 88_000_000, genres: ["Alternative Rock", "Pop"] },
];

export const albums: Album[] = [
  { id: "al1", title: "Ultimate Arijit Hits", artistId: "a1", artistName: "Arijit Singh", cover: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80", year: 2024, trackIds: ["t1", "t2", "t3"] },
  { id: "al2", title: "After Hours", artistId: "a2", artistName: "The Weeknd", cover: "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=500&q=80", year: 2020, trackIds: ["t4", "t5"] },
  { id: "al3", title: "1989 (Taylor's Version)", artistId: "a3", artistName: "Taylor Swift", cover: "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=500&q=80", year: 2023, trackIds: ["t6", "t7"] },
  { id: "al4", title: "Brahmastra & Beyond", artistId: "a4", artistName: "Pritam", cover: "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=500&q=80", year: 2022, trackIds: ["t8"] },
  { id: "al5", title: "Future Nostalgia", artistId: "a5", artistName: "Dua Lipa", cover: "https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?w=500&q=80", year: 2020, trackIds: ["t9", "t10"] },
  { id: "al6", title: "Melodies of Shreya", artistId: "a6", artistName: "Shreya Ghoshal", cover: "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=500&q=80", year: 2023, trackIds: ["t11"] },
  { id: "al7", title: "Lofi Study Beats", artistId: "a7", artistName: "Lofi Girl", cover: "https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=500&q=80", year: 2024, trackIds: ["t12"] },
  { id: "al8", title: "Music of the Spheres", artistId: "a8", artistName: "Coldplay", cover: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=500&q=80", year: 2021, trackIds: ["t13"] },
];

export const tracks: Track[] = [
  { id: "t1", title: "Kesariya", artistId: "a1", artistName: "Arijit Singh", albumId: "al1", albumTitle: "Brahmastra", cover: albums[0].cover, duration: 268, liked: true, plays: 450_000_000 },
  { id: "t2", title: "Tum Hi Ho", artistId: "a1", artistName: "Arijit Singh", albumId: "al1", albumTitle: "Aashiqui 2", cover: albums[0].cover, duration: 262, plays: 680_000_000 },
  { id: "t3", title: "Channa Mereya", artistId: "a1", artistName: "Arijit Singh", albumId: "al1", albumTitle: "Ae Dil Hai Mushkil", cover: albums[0].cover, duration: 289, plays: 390_000_000 },
  { id: "t4", title: "Blinding Lights", artistId: "a2", artistName: "The Weeknd", albumId: "al2", albumTitle: "After Hours", cover: albums[1].cover, duration: 200, liked: true, plays: 4_100_000_000 },
  { id: "t5", title: "Starboy", artistId: "a2", artistName: "The Weeknd", albumId: "al2", albumTitle: "Starboy", cover: albums[1].cover, duration: 230, plays: 2_900_000_000 },
  { id: "t6", title: "Cruel Summer", artistId: "a3", artistName: "Taylor Swift", albumId: "al3", albumTitle: "Lover", cover: albums[2].cover, duration: 178, plays: 2_100_000_000 },
  { id: "t7", title: "Blank Space", artistId: "a3", artistName: "Taylor Swift", albumId: "al3", albumTitle: "1989", cover: albums[2].cover, duration: 231, liked: true, plays: 1_800_000_000 },
  { id: "t8", title: "Tere Pyaar Mein", artistId: "a4", artistName: "Pritam & Arijit Singh", albumId: "al4", albumTitle: "Tu Jhoothi Main Makkaar", cover: albums[3].cover, duration: 266, plays: 210_000_000 },
  { id: "t9", title: "Levitating", artistId: "a5", artistName: "Dua Lipa", albumId: "al5", albumTitle: "Future Nostalgia", cover: albums[4].cover, duration: 203, plays: 2_600_000_000 },
  { id: "t10", title: "Don't Start Now", artistId: "a5", artistName: "Dua Lipa", albumId: "al5", albumTitle: "Future Nostalgia", cover: albums[4].cover, duration: 183, liked: true, plays: 2_400_000_000 },
  { id: "t11", title: "Param Sundari", artistId: "a6", artistName: "Shreya Ghoshal", albumId: "al6", albumTitle: "Mimi", cover: albums[5].cover, duration: 192, plays: 320_000_000 },
  { id: "t12", title: "Midnight Coffee", artistId: "a7", artistName: "Lofi Girl", albumId: "al7", albumTitle: "Lofi Study Beats", cover: albums[6].cover, duration: 154, plays: 85_000_000 },
  { id: "t13", title: "Yellow", artistId: "a8", artistName: "Coldplay", albumId: "al8", albumTitle: "Parachutes", cover: albums[7].cover, duration: 269, liked: true, plays: 2_300_000_000 },
];

export const playlists: Playlist[] = [
  { id: "p1", title: "Spotify Top Hits 2025", description: "The biggest tracks on Spotify worldwide right now.", cover: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80", trackIds: ["t1", "t4", "t6", "t9", "t13"], owner: "Spotify Verified", gradient: ["#1db954", "#121212"] },
  { id: "p2", title: "Bollywood Romantic Hits", description: "Best of Arijit Singh, Pritam, & Shreya Ghoshal.", cover: "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=500&q=80", trackIds: ["t1", "t2", "t3", "t8", "t11"], owner: "Meloxi Curators", gradient: ["#ff2a6d", "#9b51e0"] },
  { id: "p3", title: "Global Pop Superstars", description: "Taylor Swift, The Weeknd, Dua Lipa & more.", cover: "https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=500&q=80", trackIds: ["t4", "t5", "t6", "t7", "t9", "t10"], owner: "Spotify Verified", gradient: ["#0ea5e9", "#8b5cf6"] },
  { id: "p4", title: "Lofi Chill & Focus Beats", description: "Relaxing lo-fi beats for deep study & relaxation.", cover: "https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=500&q=80", trackIds: ["t12", "t1", "t4"], owner: "Lofi Girl", gradient: ["#f472b6", "#fb923c"] },
  { id: "p5", title: "Rock Classics & Anthems", description: "Coldplay, Imagine Dragons, & Stadium Rock.", cover: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=500&q=80", trackIds: ["t13", "t4", "t6"], owner: "Meloxi Curators", gradient: ["#f59e0b", "#22d3ee"] },
];

export const genres: Genre[] = [
  { id: "g1", name: "Bollywood", gradient: ["#ff2a6d", "#9b51e0"] },
  { id: "g2", name: "Pop", gradient: ["#1db954", "#059669"] },
  { id: "g3", name: "R&B", gradient: ["#f472b6", "#fb923c"] },
  { id: "g4", name: "Hip-Hop", gradient: ["#f59e0b", "#ef4444"] },
  { id: "g5", name: "Lo-Fi", gradient: ["#60a5fa", "#a78bfa"] },
  { id: "g6", name: "Rock", gradient: ["#38bdf8", "#8b5cf6"] },
  { id: "g7", name: "Dance", gradient: ["#ec4899", "#8b5cf6"] },
  { id: "g8", name: "Ambient", gradient: ["#a3e635", "#22d3ee"] },
];

export const moods: Mood[] = [
  { id: "m1", name: "Bollywood Romantic", emoji: "💖", gradient: ["#ff2a6d", "#9b51e0"] },
  { id: "m2", name: "Pop Energy", emoji: "⚡", gradient: ["#1db954", "#059669"] },
  { id: "m3", name: "Deep Focus", emoji: "🎯", gradient: ["#0ea5e9", "#8b5cf6"] },
  { id: "m4", name: "Workout Hits", emoji: "🔥", gradient: ["#ef4444", "#f59e0b"] },
  { id: "m5", name: "Late Night Chill", emoji: "🌙", gradient: ["#6366f1", "#22d3ee"] },
  { id: "m6", name: "Party Anthems", emoji: "✨", gradient: ["#f472b6", "#facc15"] },
];

export const lyricsByTrack: Record<string, LyricLine[]> = {
  t1: [
    { time: 0, text: "Kesariya tera ishq hai piya" },
    { time: 6, text: "Rang jaaun jo main haath lagaun" },
    { time: 12, text: "Din beete saara teri fikr mein" },
    { time: 18, text: "Rain sari teri kair maangus" },
    { time: 24, text: "Kesariya tera ishq hai piya" },
  ],
  t4: [
    { time: 0, text: "I've been on my own for long enough" },
    { time: 5, text: "Maybe you can show me how to love, maybe" },
    { time: 10, text: "I'm going through withdrawals" },
    { time: 15, text: "You don't even have to do too much" },
    { time: 20, text: "I said, ooh, I'm blinded by the lights" },
  ],
};

export function trackById(id: string): Track | undefined { return tracks.find((t) => t.id === id); }
export function albumById(id: string): Album | undefined { return albums.find((a) => a.id === id); }
export function artistById(id: string): Artist | undefined { return artists.find((a) => a.id === id); }
export function playlistById(id: string): Playlist | undefined { return playlists.find((p) => p.id === id); }
export function tracksByIds(ids: string[]): Track[] { return ids.map(trackById).filter(Boolean) as Track[]; }
export function artistAlbums(artistId: string): Album[] { return albums.filter((a) => a.artistId === artistId); }
export function artistTopTracks(artistId: string): Track[] { return tracks.filter((t) => t.artistId === artistId); }
export function relatedArtists(artistId: string): Artist[] { return artists.filter((a) => a.id !== artistId).slice(0, 5); }
