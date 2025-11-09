CREATE TABLE IF NOT EXISTS predictions (
  id serial PRIMARY KEY,
  timestamp timestamptz DEFAULT now(),
  source text,
  image_width integer,
  image_height integer,
  predictions jsonb
);
