import os
import pandas as pd
import numpy as np

def run_comprehensive_verification():
    print("=" * 70)
    print("        NETFLIX DECISIONAL DATABASE COMPREHENSIVE VALIDATION")
    print("=" * 70)
    
    base_dir = r"C:\Users\hp\Desktop\Projet BI Netflix"
    data_dir = os.path.join(base_dir, "data")
    
    original_path = os.path.join(data_dir, "netflix.csv")
    fact_path = os.path.join(data_dir, "F_Netflix.csv")
    
    dims = {
        "DimType": os.path.join(data_dir, "DimType.csv"),
        "DimRating": os.path.join(data_dir, "DimRating.csv"),
        "DimDate": os.path.join(data_dir, "DimDate.csv"),
        "DimGenre": os.path.join(data_dir, "DimGenre.csv"),
        "DimCountry": os.path.join(data_dir, "DimCountry.csv"),
        "DimDirector": os.path.join(data_dir, "DimDirector.csv"),
        "DimActor": os.path.join(data_dir, "DimActor.csv")
    }
    
    # 1. Check if files exist
    all_files_exist = True
    print("[1/6] Vérification de l'existence des fichiers...")
    for name, path in [("netflix.csv", original_path), ("F_Netflix.csv", fact_path)] + list(dims.items()):
        if not os.path.exists(path):
            print(f"  [ERREUR] Fichier introuvable : {os.path.basename(path)}")
            all_files_exist = False
        else:
            print(f"  [OK] Fichier trouvé : {os.path.basename(path)}")
            
    if not all_files_exist:
        print("\n[ERREUR CRITIQUE] Validation abandonnée : certains fichiers sont manquants.")
        return
        
    print("\nChargement des jeux de données...")
    df_orig = pd.read_csv(original_path)
    df_fact = pd.read_csv(fact_path)
    df_type = pd.read_csv(dims["DimType"])
    df_rating = pd.read_csv(dims["DimRating"])
    df_date = pd.read_csv(dims["DimDate"])
    df_genre = pd.read_csv(dims["DimGenre"])
    df_country = pd.read_csv(dims["DimCountry"])
    df_director = pd.read_csv(dims["DimDirector"])
    df_actor = pd.read_csv(dims["DimActor"])
    
    errors = 0
    warnings = 0
    
    # 2. Row Count & Primary Key Checks
    print("\n" + "-"*70)
    print("[2/6] CONTRÔLE DE VOLUMÉTRIE & CLÉS PRIMAIRES")
    print("-"*70)
    
    orig_rows = len(df_orig)
    fact_rows = len(df_fact)
    print(f"  Nombre de lignes - Source originale:  {orig_rows}")
    print(f"  Nombre de lignes - Table de faits F:  {fact_rows}")
    
    if orig_rows != fact_rows:
        print(f"  [ERREUR] Volumétrie incohérente ! Source = {orig_rows}, Faits = {fact_rows}")
        errors += 1
    else:
        print("  [OK] Les nombres de lignes correspondent.")
        
    fact_unique_shows = df_fact["show_id"].nunique()
    if fact_unique_shows != fact_rows:
        print(f"  [ERREUR] La colonne show_id de F_Netflix a des doublons ! (Clé primaire invalide)")
        errors += 1
    else:
        print("  [OK] show_id est une clé primaire unique valide dans la table de faits.")
        
    # 3. Referential Integrity Checks
    print("\n" + "-"*70)
    print("[3/6] INTÉGRITÉ RÉFÉRENTIELLE (Clés Étrangères)")
    print("-"*70)
    
    # TypeKey
    fact_types = set(df_fact["TypeKey"].dropna().unique())
    dim_types = set(df_type["TypeKey"].unique())
    type_orphans = fact_types - dim_types
    if type_orphans:
        print(f"  [ERREUR] Clés TypeKey orphelines dans la table de faits: {type_orphans}")
        errors += 1
    else:
        print("  [OK] Toutes les TypeKeys de la table de faits existent dans DimType.")
        
    # RatingKey
    fact_ratings = set(df_fact["RatingKey"].dropna().unique())
    dim_ratings = set(df_rating["RatingKey"].unique())
    rating_orphans = fact_ratings - dim_ratings
    if rating_orphans:
        print(f"  [ERREUR] Clés RatingKey orphelines dans la table de faits: {rating_orphans}")
        errors += 1
    else:
        print("  [OK] Toutes les RatingKeys de la table de faits existent dans DimRating.")
        
    # DateKey
    fact_dates = set(df_fact["DateKey"].dropna().astype(int).unique())
    dim_dates = set(df_date["DateKey"].unique())
    date_orphans = fact_dates - dim_dates
    if date_orphans:
        print(f"  [ERREUR] Clés DateKey orphelines dans F_Netflix (absentes de DimDate): {len(date_orphans)} clés.")
        errors += 1
    else:
        print("  [OK] Toutes les DateKeys non-nulles de la table de faits existent dans DimDate.")
        
    null_date_keys = df_fact["DateKey"].isnull().sum()
    if null_date_keys > 0:
        print(f"  [ATTENTION] {null_date_keys} shows n'ont pas de DateKey (vide).")
        print("              Ceci est normal si date_added était manquant dans les données sources.")
        warnings += 1

    # Check exploded dimensions (should have zero orphan show_ids)
    for name, df_dim in [("DimGenre", df_genre), ("DimCountry", df_country), ("DimDirector", df_director), ("DimActor", df_actor)]:
        dim_shows = set(df_dim["show_id"].unique())
        fact_shows = set(df_fact["show_id"].unique())
        
        orphans_in_dim = dim_shows - fact_shows
        if orphans_in_dim:
            print(f"  [ERREUR] La dimension {name} contient des show_ids absents de la table de faits : {len(orphans_in_dim)} orphelins.")
            errors += 1
        else:
            print(f"  [OK] Tous les show_ids de {name} existent dans la table de faits.")

    # 4. Case-Sensitivity & Case-Duplicates Check
    print("\n" + "-"*70)
    print("[4/6] ANALYSE DE CASSE (Sensibilité aux variations de Majuscules)")
    print("-"*70)
    
    for name, col, df_dim in [("Directeurs", "Director", df_director), ("Acteurs", "Actor", df_actor), ("Pays", "Country", df_country)]:
        sens_count = df_dim[col].nunique()
        insens_count = df_dim[col].str.lower().nunique()
        diff = sens_count - insens_count
        
        if diff > 0:
            print(f"  [INFO] Dimension {name} : {diff} doublons dus uniquement à des différences de majuscules.")
            print(f"         (Compte sensible: {sens_count} | Compte insensible: {insens_count})")
            print("         *Note : Power BI regroupera ces valeurs. C'est normal si votre distinctcount y est plus bas.*")
            # List top 2 examples
            unique_vals = pd.Series(df_dim[col].unique())
            dup_mask = unique_vals.str.lower().duplicated(keep=False)
            examples = unique_vals[dup_mask].sort_values(key=lambda x: x.str.lower()).head(4).tolist()
            print(f"         Exemples de doublons : {', '.join(examples)}")
        else:
            print(f"  [OK] Dimension {name} : Aucune variation de casse détectée (Compte unique = {sens_count}).")

    # 5. Core Distributions for Power BI Verification
    print("\n" + "-"*70)
    print("[5/6] DISTRIBUTIONS & CHIFFRES CLÉS POUR VOS VISUELS PBI")
    print("-"*70)
    
    # 5.1 added year
    df_merged_date = df_fact.merge(df_date, on="DateKey", how="left")
    by_year = df_merged_date.groupby("Year", dropna=False)["show_id"].count().reset_index()
    by_year.columns = ["Année d'ajout", "Nombre de titres"]
    by_year = by_year.sort_values("Année d'ajout")
    
    print("\n  >>> TITRES AJOUTÉS PAR ANNÉE (Axe Temporel) :")
    print(by_year.to_string(index=False, justify='left'))
    
    # 5.2 genre
    by_genre = df_genre.groupby("Genre")["show_id"].count().reset_index()
    by_genre.columns = ["Genre", "Nombre de titres"]
    by_genre = by_genre.sort_values("Nombre de titres", ascending=False)
    print("\n  >>> TOP 10 GENRES :")
    print(by_genre.head(10).to_string(index=False, justify='left'))
    
    # 5.3 rating
    df_merged_rating = df_fact.merge(df_rating, on="RatingKey", how="left")
    by_rating = df_merged_rating.groupby("rating", dropna=False)["show_id"].count().reset_index()
    by_rating.columns = ["Classification (Rating)", "Nombre de titres"]
    by_rating = by_rating.sort_values("Nombre de titres", ascending=False)
    print("\n  >>> NOMBRE DE TITRES PAR RATING :")
    print(by_rating.to_string(index=False, justify='left'))

    # 6. Dashboard Reconciliation Summary Table
    print("\n" + "=" * 70)
    print("      SYNTHÈSE DE RÉCONCILIATION POUR LE TABLEAU DE BORD")
    print("=" * 70)
    
    df_fact_type = df_fact.merge(df_type, on="TypeKey", how="left")
    fact_type_counts = df_fact_type["type"].value_counts().to_dict()
    
    print(f"  1. Nombre total de Shows :               {fact_rows}")
    print(f"  2. Total Films (Movies) :               {fact_type_counts.get('Movie', 0)}")
    print(f"  3. Total Séries (TV Shows) :            {fact_type_counts.get('TV Show', 0)}")
    print(f"  4. Total de lignes de Genres :           {len(df_genre)}")
    print(f"  5. Nombre de Genres uniques :           {df_genre['Genre'].nunique()}")
    print(f"  6. Total de lignes de Pays :             {len(df_country)}")
    print(f"  7. Nombre de Pays uniques :             {df_country['Country'].nunique()}")
    print(f"  8. Total de lignes de Réalisateurs :     {len(df_director)}")
    print(f"  9. Réalisateurs uniques (sensible) :     {df_director['Director'].nunique()}")
    print(f"     Réalisateurs uniques (insensible/PBI): {df_director['Director'].str.lower().nunique()}")
    print(f"  10. Total de lignes d'Acteurs :          {len(df_actor)}")
    print(f"      Acteurs uniques (sensible) :         {df_actor['Actor'].nunique()}")
    print(f"      Acteurs uniques (insensible/PBI) :   {df_actor['Actor'].str.lower().nunique()}")
    print(f"  11. Shows sans date d'ajout :            {null_date_keys}")
    
    print("\n" + "=" * 70)
    if errors == 0:
        print(f"  RÉSULTAT : VALIDATION RÉUSSIE ({errors} Erreur, {warnings} Avertissement).")
        print("  Vos CSV sont cohérents et prêts à être importés dans Power BI.")
    else:
        print(f"  RÉSULTAT : VALIDATION ÉCHOUÉE ({errors} Erreurs, {warnings} Avertissements).")
        print("  Veuillez vérifier les messages [ERREUR] ci-dessus.")
    print("=" * 70)

if __name__ == "__main__":
    run_comprehensive_verification()
