package com.soumya.lore.navigation

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.soumya.lore.ui.screens.HomeScreen
import com.soumya.lore.ui.screens.LoadingScreen
import com.soumya.lore.ui.screens.ResultScreen

private const val QUERY_ARG = "query"
private const val HOME_ROUTE = "home"
private const val LOADING_ROUTE = "loading/{$QUERY_ARG}"
private const val RESULT_ROUTE = "result/{$QUERY_ARG}"

/**
 * Single source of truth for how screens connect: Home -> Loading -> Result.
 * The query is passed forward as a nav argument rather than a shared
 * ViewModel, since there's no shared state to manage yet.
 */
@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = HOME_ROUTE) {
        composable(HOME_ROUTE) {
            HomeScreen(
                onSearch = { query ->
                    navController.navigate("loading/$query")
                }
            )
        }

        composable(
            route = LOADING_ROUTE,
            arguments = listOf(navArgument(QUERY_ARG) { type = NavType.StringType })
        ) { backStackEntry ->
            val query = backStackEntry.arguments?.getString(QUERY_ARG).orEmpty()
            LoadingScreen(
                query = query,
                onComplete = {
                    navController.navigate("result/$query") {
                        // Replace Loading in the back stack so the user can't
                        // navigate "back" into a finished loading screen.
                        popUpTo(HOME_ROUTE)
                    }
                }
            )
        }

        composable(
            route = RESULT_ROUTE,
            arguments = listOf(navArgument(QUERY_ARG) { type = NavType.StringType }),
            // Fast, minimal fade rather than the default slide/crossfade —
            // the Loading screen already ends on a static card silhouette
            // matching Result's AnswerCard, so this should read as a
            // continuation of that animation, not a screen change.
            enterTransition = { fadeIn(tween(120)) },
            exitTransition = { fadeOut(tween(80)) }
        ) { backStackEntry ->
            val query = backStackEntry.arguments?.getString(QUERY_ARG).orEmpty()
            ResultScreen(
                query = query,
                onBack = { navController.popBackStack() },
                onNewSearch = { navController.popBackStack() }
            )
        }
    }
}
