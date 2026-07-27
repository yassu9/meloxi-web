export type ID = string;

export interface Artist {
  id: ID;
  name: string;
  image: string;
  banner?: string;
  bio?: string;
  monthlyListeners?: number;
  genres?: string[];
}

export interface Album {
  id: ID;
  title: string;
  artistId: ID;
  artistName: string;
  cover: string;
  year: number;
  trackIds: ID[];
}

export interface Track {
  id: ID;
  title: string;
  artistId: ID;
  artistName: string;
  albumId: ID;
  albumTitle: string;
  cover: string;
  duration: number; // seconds
  liked?: boolean;
  plays?: number;
}

export interface Playlist {
  id: ID;
  title: string;
  description: string;
  cover: string;
  trackIds: ID[];
  owner: string;
  gradient?: [string, string];
}

export interface Genre {
  id: ID;
  name: string;
  gradient: [string, string];
}

export interface Mood {
  id: ID;
  name: string;
  emoji: string;
  gradient: [string, string];
}

export interface LyricLine {
  time: number;
  text: string;
}
